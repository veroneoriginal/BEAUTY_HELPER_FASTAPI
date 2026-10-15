# infrastructure/celery/tasks.py

import asyncio
import json
import logging
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import select, update
from sqlalchemy.orm import joinedload

from apps.balance.models import BalanceOperation, UserBalance  # noqa: F401
from apps.balance.sync_repository import SyncBalanceRepository
from apps.balance.sync_services import SyncBalanceService
from apps.content_generation.openai.task_processing.main import TaskProcessing
from apps.content_generation.openai.utils.utils_errors import (
    OpenAIAuthError,
    OpenAIInsufficientQuotaError,
)
from apps.orchestrator.encoders import CustomJSONEncoder
from apps.package.models import Package, UserPackage  # noqa: F401
from apps.parser.exceptions import ParserError
from apps.parser.media import ImageUploader
from apps.parser.proxy.models import Proxy
from apps.parser.proxy.pool import ProxyPool
from apps.parser.proxy.source import load_from_file, load_from_site
from apps.parser.proxy.store import load_proxies, save_proxies
from apps.parser.service import ProductParser
from apps.pdf_generation.main import generate_selection_pdf
from apps.pdf_generation.utils import (
    calculate_price_full_request,
    convert_analysis_to_pdf_data,
    convert_json_openai_to_list,
)
from apps.products.models import Product, ProductFillStatus
from apps.products.product_service import ProductService
from apps.products.sync_repository import SyncProductRepository
from apps.selection.models import (
    Selection,
    SelectionStatus,
    SelectionTaskType,
)
from apps.users.models import User  # noqa: F401
from apps.waiting.models import Waiting, WaitingStatus
from core.config import settings
from core.database import sync_session
from infrastructure.celery.app import celery_app
from infrastructure.s3.service import s3_service

logger = logging.getLogger(__name__)

redis_client = Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD,
    db=0,
)

# Сколько секунд подборка может «молчать» в PROCESS (updated_at не меняется),
# прежде, чем счесть задачу зависшей и перезапустить. Не меньше TTL Redis-lock
# задачи (selection_lock, SELECTION_LOCK_SECONDS), иначе перезапуск упрётся
# в живой lock.
STUCK_PROCESS_SECONDS = 600

# TTL lock'а генерации. Продлевается после каждого шага OpenAI: длинный
# состав идёт дольше 10 минут, и без продления lock истёк бы посреди работы.
SELECTION_LOCK_SECONDS = 600

# Сколько секунд подборка может пробыть в PARSING, прежде чем beat-страховка
# разберётся с ней сама. Больше TTL parse_lock (45 мин) — к этому моменту
# lock упавшей задачи точно истёк, и перезапуск парсинга не упрётся в него.
STUCK_PARSING_SECONDS = 50 * 60


@contextmanager
def redis_lock(lock_name: str, expire: int = 55):
    """
    Контекстный менеджер для блокировки повторного запуска задачи через Redis.
    Устанавливает ключ в Redis на время выполнения задачи.

    :param lock_name: имя блокировки — ключ в Redis
    :param expire: время жизни блокировки в секундах
    """

    # Установка ключа в Redis с условием.
    try:
        lock_acquired = redis_client.set(lock_name, "locked", ex=expire, nx=True)
    except RedisError as e:
        logger.error(
            "[REDIS_LOCK] Redis недоступен при захвате блокировки '%s': %s",
            lock_name,
            e,
        )
        raise

    try:
        yield lock_acquired
    finally:
        if lock_acquired:
            try:
                redis_client.delete(lock_name)
            except RedisError as e:
                logger.warning(
                    "[REDIS_LOCK] Не удалось снять блокировку '%s': %s",
                    lock_name,
                    e,
                )


def _get_selection_with_product(
    session,
    selection_id: int,
) -> Selection | None:
    """
    Получает подборку вместе с продуктом по ID через синхронную сессию.

    :param session: синхронная сессия SQLAlchemy
    :param selection_id: ID подборки
    :return: объект Selection или None
    """

    result = session.execute(
        select(Selection)
        .options(joinedload(Selection.product))
        .where(Selection.id == selection_id)
    )
    return result.scalar_one_or_none()


def _selection_lock_name(selection_id: int) -> str:
    """
    Ключ Redis-lock генерации подборки.
    """
    return f"selection_lock:{selection_id}"


def _extend_selection_lock(selection_id: int) -> None:
    """
    Продлевает lock генерации ещё на SELECTION_LOCK_SECONDS.
    Redis недоступен — только лог: генерация важнее продления.
    """
    try:
        redis_client.expire(_selection_lock_name(selection_id), SELECTION_LOCK_SECONDS)
    except RedisError as exc:
        logger.warning(
            "[REDIS_LOCK] Не удалось продлить lock подборки %s: %s", selection_id, exc
        )


def _run_openai_analysis(session, selection: Selection, dto: dict) -> None:
    """
    Анализ через OpenAI с сохранением после каждого шага.

    Запросы и ответы готовых шагов и номер последнего из них
    (analysis_last_step) коммитятся в подборку сразу после шага.
    Упадёт 5-й шаг из 8 или PDF/S3 — rollback их не откатит, и повтор
    задачи продолжит со следующего шага, а не заплатит OpenAI ещё раз.
    Все шаги уже готовы — OpenAI не зовём совсем.
    Цена считается по ответам всех шагов и коммитится вместе с последним.
    После каждого шага продлевается lock генерации.

    :param session: синхронная сессия SQLAlchemy
    :param selection: объект подборки
    :param dto: данные продукта для промптов
    """

    last_done_step = selection.analysis_last_step or 0
    if last_done_step:
        logger.info(
            "[OPENAI] Подборка %s: шаги 1–%s уже готовы, продолжаем",
            selection.id,
            last_done_step,
        )

    def save_step(step_number: int) -> None:
        """
        Пишет в подборку все готовые шаги и коммитит.
        """
        selection.request_details = json.dumps(
            work_task_processing.request_data,
            ensure_ascii=False,
            indent=2,
        )
        selection.final_analysis = json.dumps(
            work_task_processing.response_data,
            ensure_ascii=False,
            indent=2,
            cls=CustomJSONEncoder,
        )
        selection.analysis_last_step = step_number
        session.commit()
        _extend_selection_lock(selection.id)
        logger.info("[OPENAI] Подборка %s: шаг %s сохранён", selection.id, step_number)

    work_task_processing = TaskProcessing(
        collection_data=dto,
        task_type=SelectionTaskType(selection.task_type),
        request_data=(
            json.loads(selection.request_details) if last_done_step else None
        ),
        response_data=(
            json.loads(selection.final_analysis) if last_done_step else None
        ),
        last_done_step=last_done_step,
        on_step_done=save_step,
    )

    logger.info("[OPENAI] Run task processing")
    work_task_processing.run_task_processing()

    if not work_task_processing.response_data:
        raise ValueError("final_analysis пустой — OpenAI не вернул ответ")

    # Считаем стоимость по всем шагам: и этой попытки, и прошлых
    selection.price = calculate_price_full_request(
        answer_from_openai=convert_json_openai_to_list(
            analysis_data=selection.final_analysis,
        ),
    )
    session.commit()

    logger.info("[PRICE] Подборка %s: price=%s", selection.id, selection.price)


def _create_selection_on_task(session, selection: Selection) -> None:
    """
    Основная логика генерации подборки:
    1. Получает DTO продукта
    2. Отправляет запрос в OpenAI (пошагово)
    3. Сохраняет запросы и ответы в подборку после каждого шага;
       при повторе задачи готовые шаги в OpenAI не отправляются
    4. Генерирует PDF
    5. Загружает PDF на S3
    6. Сохраняет ссылку на PDF

    :param session: синхронная сессия SQLAlchemy
    :param selection: объект подборки
    """

    # 1. Получаем DTO продукта
    product = selection.product
    dto = asdict(product.get_data_about_product())

    logger.info(
        "[CREATE_SELECTION] Product DTO prepared. Keys=%s",
        list(dto.keys()),
    )

    # 2–5. Анализ через OpenAI. Повтор задачи после сбоя продолжает
    # с первого неготового шага; все готовы — сразу к PDF.
    _run_openai_analysis(session, selection, dto)

    answer_from_openai = convert_json_openai_to_list(
        analysis_data=selection.final_analysis,
    )

    # 6. Генерируем PDF
    analysis_to_pdf = convert_analysis_to_pdf_data(
        answer_from_openai=answer_from_openai,
    )
    pdf_url = generate_selection_pdf(
        task_type=SelectionTaskType(selection.task_type),
        product_data=dto,
        analysis=analysis_to_pdf,
    )

    logger.info("[PDF] Generated pdf_url=%s", pdf_url)

    if not pdf_url:
        raise RuntimeError("PDF не был загружен на S3 — pdf_url пустой")

    # 7. Сохраняем ссылку на PDF и меняем статус на DONE
    selection.pdf_url = pdf_url
    selection.selection_status = SelectionStatus.DONE
    session.flush()

    logger.info("[Finished] Finished selection_id=%s", selection.id)


def _close_waiting_and_act(
    session, waiting: Waiting, balance_service, action: str
) -> None:
    """
    Атомарно закрывает ожидание и выполняет действие с балансом.
    Если ожидание уже закрыто другим воркером (rowcount=0) — пропускает.

    :param action: "confirm" — списать крутку, "release" — вернуть крутку
    """
    result = session.execute(
        update(Waiting)
        .where(Waiting.id == waiting.id, Waiting.status == WaitingStatus.OPEN)
        .values(status=WaitingStatus.CLOSED)
    )
    if result.rowcount != 1:
        return

    if action == "confirm":
        balance_service.confirm_spins(user_id=waiting.user_id)
        logger.info(
            "[WAITING] Закрыто waiting_id=%s для user_id=%s",
            waiting.id,
            waiting.user_id,
        )
    else:
        balance_service.release_spins(user_id=waiting.user_id)
        logger.info(
            "[WAITING] Возвращена крутка waiting_id=%s для user_id=%s",
            waiting.id,
            waiting.user_id,
        )

    session.flush()


def _get_open_waitings(session, selection_id: int) -> list:
    """
    Возвращает все открытые (OPEN) ожидания по подборке.

    :param session: синхронная сессия SQLAlchemy
    :param selection_id: ID подборки
    :return: список объектов Waiting со статусом OPEN
    """
    return (
        session.execute(
            select(Waiting).where(
                Waiting.selection_id == selection_id,
                Waiting.status == WaitingStatus.OPEN,
            )
        )
        .scalars()
        .all()
    )


def _complete_waitings_for_selection(session, selection: Selection) -> None:
    """
    Закрывает все открытые ожидания подборки и списывает крутку каждому
    пользователю (подборка успешно готова).

    :param session: синхронная сессия SQLAlchemy
    :param selection: объект подборки
    """
    balance_service = SyncBalanceService(SyncBalanceRepository(session))
    for waiting in _get_open_waitings(session, selection.id):
        _close_waiting_and_act(session, waiting, balance_service, action="confirm")


def _release_spins_for_selection(session, selection_id: int) -> None:
    """
    Закрывает все открытые ожидания подборки и возвращает крутку каждому
    пользователю (подборка завершилась ошибкой).

    :param session: синхронная сессия SQLAlchemy
    :param selection_id: ID подборки
    """
    balance_service = SyncBalanceService(SyncBalanceRepository(session))
    for waiting in _get_open_waitings(session, selection_id):
        _close_waiting_and_act(session, waiting, balance_service, action="release")


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
)
def run_create_selection_on_task(self, selection_id: int) -> None:
    """
    Celery-задача для генерации подборки.
    Запускается сразу через .delay() когда пользователь отправил ссылку.

    Шаги:
    1. Меняет статус на PROCESS
    2. Запускает генерацию (OpenAI → PDF → S3)
    3. Закрывает все ожидания, списывает крутку
    4. При ошибке — помечает FAILED, возвращает крутку, retry

    :param selection_id: ID подборки
    """
    with redis_lock(
        _selection_lock_name(selection_id), expire=SELECTION_LOCK_SECONDS
    ) as acquired:
        if not acquired:
            logger.info(
                "[TASK] Подборка %s уже обрабатывается, пропускаем", selection_id
            )
            return

        with sync_session() as session:
            selection = _get_selection_with_product(session, selection_id)

            if not selection:
                logger.error("[TASK] Подборка %s не найдена", selection_id)
                return

            if selection.selection_status == SelectionStatus.DONE:
                logger.info(
                    "[TASK] Подборка %s уже завершена, пропускаем", selection_id
                )
                return

            # Меняем статус на PROCESS и СРАЗУ коммитим, чтобы он стал виден
            # остальным соединениям. Иначе на всё время генерации (OpenAI + PDF)
            # подборка для всех остаётся QUEUE — и beat-страховка может счесть её
            # незапущенной и перезапустить, плодя дубли.
            selection.selection_status = SelectionStatus.PROCESS
            session.commit()

            try:
                _create_selection_on_task(session=session, selection=selection)
                _complete_waitings_for_selection(session=session, selection=selection)
                session.commit()

                logger.info("[TASK] Подборка %s успешно завершена", selection_id)

            # Кончились деньги или неверный ключ — повтор не поможет:
            # сразу FAILED и возврат крутки, без retry
            except (OpenAIInsufficientQuotaError, OpenAIAuthError) as exc:
                logger.critical("❌ %s", exc)
                session.rollback()
                selection = _get_selection_with_product(session, selection_id)
                selection.selection_status = SelectionStatus.FAILED
                selection.error_message = str(exc)
                _release_spins_for_selection(session, selection_id)
                session.commit()

            except Exception as exc:
                logger.error(
                    "[TASK] Ошибка генерации подборки selection_id=%s error=%s",
                    selection_id,
                    exc,
                )
                session.rollback()
                if self.request.retries >= self.max_retries:
                    selection = _get_selection_with_product(session, selection_id)
                    selection.selection_status = SelectionStatus.FAILED
                    selection.error_message = str(exc)
                    _release_spins_for_selection(session, selection_id)
                session.commit()

                raise self.retry(exc=exc)


def _continue_selections_after_parse(session, product: Product) -> None:
    """
    Двигает дальше все подборки продукта в статусе PARSING по итогу парсинга.

    - продукт DONE → подборки QUEUE и запуск генерации;
    - продукт FAILED / INCOMPLETE → подборки FAILED, причина из last_error,
      ожидающим (кто присоединился во время парсинга) возвращается крутка.

    Подборки берём условным UPDATE ... WHERE status = PARSING: если их
    одновременно двигает beat-страховка, каждую подборку двинет только один.

    :param session: синхронная сессия SQLAlchemy
    :param product: продукт с итоговым fill_status (DONE / FAILED / INCOMPLETE)
    """
    if product.fill_status == ProductFillStatus.DONE:
        selection_ids = (
            session.execute(
                update(Selection)
                .where(
                    Selection.product_id == product.id,
                    Selection.selection_status == SelectionStatus.PARSING,
                )
                .values(selection_status=SelectionStatus.QUEUE)
                .returning(Selection.id)
            )
            .scalars()
            .all()
        )
        # Коммитим до .delay(), чтобы задача генерации видела QUEUE
        session.commit()

        for selection_id in selection_ids:
            run_create_selection_on_task.delay(selection_id=selection_id)
            logger.info(
                "[PARSE] Продукт %s спарсен, подборка %s отправлена на генерацию",
                product.id,
                selection_id,
            )
        return

    selection_ids = (
        session.execute(
            update(Selection)
            .where(
                Selection.product_id == product.id,
                Selection.selection_status == SelectionStatus.PARSING,
            )
            .values(
                selection_status=SelectionStatus.FAILED,
                error_message=product.last_error,
            )
            .returning(Selection.id)
        )
        .scalars()
        .all()
    )
    for selection_id in selection_ids:
        _release_spins_for_selection(session, selection_id)
        logger.warning(
            "[PARSE] Продукт %s не спарсен (%s), подборка %s → FAILED",
            product.id,
            product.fill_status,
            selection_id,
        )
    session.commit()


def _check_stuck_parsing(session) -> None:
    """
    Beat-страховка для подборок в PARSING дольше STUCK_PARSING_SECONDS.
    Ищем по подборкам, а не по ожиданиям: парсинг — один на продукт,
    сколько бы подборок и ожиданий на нём ни висело.

    По fill_status продукта:
    - DONE / FAILED / INCOMPLETE → подборки дальше, как в конце задачи парсинга;
    - EMPTY / IN_PROGRESS → задача потерялась или воркер умер — парсим заново.

    :param session: синхронная сессия SQLAlchemy
    """
    now = datetime.now(timezone.utc)
    selections = (
        session.execute(
            select(Selection).where(
                Selection.selection_status == SelectionStatus.PARSING,
                Selection.updated_at < now - timedelta(seconds=STUCK_PARSING_SECONDS),
            )
        )
        .scalars()
        .all()
    )

    # Несколько подборок одного продукта (разные task_type) — один парсинг
    products = {selection.product_id: selection.product for selection in selections}

    for product_id, product in products.items():
        if product.fill_status in (
            ProductFillStatus.DONE,
            ProductFillStatus.FAILED,
            ProductFillStatus.INCOMPLETE,
        ):
            logger.warning(
                "[WAITING_TASK] Подборки продукта %s зависли в PARSING, продукт %s",
                product_id,
                product.fill_status,
            )
            _continue_selections_after_parse(session, product)
            continue

        # Сдвигаем updated_at, чтобы следующая проверка была через
        # STUCK_PARSING_SECONDS, а не через 30 секунд
        for selection in selections:
            if selection.product_id == product_id:
                selection.updated_at = now

        run_parse_product_task.delay(product_id=product_id)
        logger.warning(
            "[WAITING_TASK] Перезапуск парсинга продукта %s (%s, подборки в PARSING)",
            product_id,
            product.fill_status,
        )


@celery_app.task
def run_waiting_task() -> None:
    """
    Периодическая задача (Celery Beat) — страховочная проверка.
    Запускается каждые 30 секунд.

    Находит все открытые ожидания и действует по статусу подборки:
    - DONE → списывает крутку, закрывает ожидание
    - FAILED → возвращает крутку, закрывает ожидание
    - QUEUE/PROCESS → перезапускает генерацию если зависла

    Отдельно проверяет подборки, зависшие в PARSING (_check_stuck_parsing).
    """
    with redis_lock("waiting_lock", expire=55) as acquired:
        if not acquired:
            logger.info("[WAITING_TASK] Задача уже выполняется.")
            return

        with sync_session() as session:
            waitings = (
                session.execute(
                    select(Waiting)
                    .options(
                        joinedload(Waiting.selection),
                    )
                    .where(Waiting.status == WaitingStatus.OPEN)
                )
                .scalars()
                .all()
            )

            logger.info(
                "[WAITING_TASK] Найдено %s открытых ожиданий",
                len(waitings),
            )

            balance_service = SyncBalanceService(SyncBalanceRepository(session))

            for waiting in waitings:
                selection = waiting.selection

                if selection.selection_status == SelectionStatus.DONE:
                    _close_waiting_and_act(
                        session, waiting, balance_service, action="confirm"
                    )

                elif selection.selection_status == SelectionStatus.FAILED:
                    _close_waiting_and_act(
                        session, waiting, balance_service, action="release"
                    )

                elif selection.selection_status == SelectionStatus.QUEUE:
                    # Возраст — от последнего изменения, а не от создания:
                    # после долгого парсинга подборка попадает в QUEUE
                    # «старой» по created_at, и генерация ставилась бы дважды
                    age_seconds = (
                        datetime.now(timezone.utc) - selection.updated_at
                    ).total_seconds()

                    if age_seconds < 60:
                        logger.info(
                            "[WAITING_TASK] Подборка id=%s в QUEUE только %s сек — пропускаем",
                            selection.id,
                            int(age_seconds),
                        )
                        continue

                    # Перезапускаем если задача зависла
                    selection.selection_status = SelectionStatus.PROCESS
                    run_create_selection_on_task.delay(selection_id=selection.id)
                    logger.info(
                        "[WAITING_TASK] Перегенерация подборки id=%s (зависла %s сек)",
                        selection.id,
                        int(age_seconds),
                    )

                elif selection.selection_status == SelectionStatus.PROCESS:
                    # Подборка взята в работу. Если воркер умер, она зависнет
                    # в PROCESS навсегда (updated_at перестаёт обновляться),
                    # а её Waiting останется OPEN — крутка заморожена.
                    # Перезапускаем, когда с последнего изменения прошло больше
                    # TTL Redis-lock: иначе .delay() упрётся в ещё живой lock и
                    # просто пропустится. Крутки здесь не трогаем — ими владеет
                    # сама задача (confirm при DONE / release при FAILED).
                    age_seconds = (
                        datetime.now(timezone.utc) - selection.updated_at
                    ).total_seconds()

                    if age_seconds < STUCK_PROCESS_SECONDS:
                        continue

                    run_create_selection_on_task.delay(selection_id=selection.id)
                    logger.warning(
                        "[WAITING_TASK] Перезапуск зависшей подборки id=%s "
                        "(в PROCESS без изменений %s сек)",
                        selection.id,
                        int(age_seconds),
                    )

            session.commit()

            _check_stuck_parsing(session)
            session.commit()


# Парсер создаётся один раз на процесс воркера (при первой задаче):
# пул прокси живёт между задачами, выкинутые прокси не возвращаются.
# Пул пересоздаётся, когда:
# - в Redis появился список новее того, из которого собран пул
#   (refresh_proxies_task обновляет его раз в час);
# - пул опустел (все выкинуты) — иначе воркер до перезапуска отвечал бы
#   NoAliveProxy на каждый парсинг.
# В Redis пусто или он недоступен — берём proxies.txt.
# При импорте модуля не создаём — tasks.py импортирует и API.
_parser: ProductParser | None = None
# Время обновления списка из Redis, из которого собран _parser;
# None — пул собран из proxies.txt
_parser_proxies_updated_at: datetime | None = None


def _load_stored_proxies() -> tuple[datetime, list[Proxy]] | None:
    """
    Список прокси из Redis или None, если его там нет или он пустой.
    Redis недоступен — тоже None: парсинг не должен падать из-за этого.
    """
    try:
        stored = load_proxies(redis_client)
    except RedisError as exc:
        logger.warning("[PARSE] Redis недоступен, прокси берём из файла: %s", exc)
        return None

    if stored is None or not stored[1]:
        return None
    return stored


def _get_parser() -> ProductParser:
    """
    Парсер с пулом прокси и общим s3_service.
    Пул — из списка в Redis, если он есть, иначе из settings.PARSER_PROXIES_FILE.
    Список в Redis обновился или пул пуст — создаём парсер заново.
    """
    global _parser, _parser_proxies_updated_at

    stored = _load_stored_proxies()
    updated_at = stored[0] if stored else None

    if (
        _parser is not None
        and len(_parser.pool) > 0
        and updated_at == _parser_proxies_updated_at
    ):
        return _parser

    if stored:
        proxies = stored[1]
        logger.info(
            "[PARSE] Пул прокси загружен из Redis (обновлён %s): %s шт.",
            updated_at.isoformat(timespec="minutes"),
            len(proxies),
        )
    else:
        proxies = load_from_file(Path(settings.PARSER_PROXIES_FILE))
        logger.info(
            "[PARSE] Пул прокси загружен из %s: %s шт.",
            settings.PARSER_PROXIES_FILE,
            len(proxies),
        )

    _parser = ProductParser(ProxyPool(proxies), ImageUploader(s3_service))
    _parser_proxies_updated_at = updated_at
    return _parser


# Худший случай парсинга: ~29 прокси × (10 с проверка + 60 с карточка) ≈ 35 мин.
# По истечении Celery бросает SoftTimeLimitExceeded → except Exception → FAILED.
PARSE_SOFT_TIME_LIMIT_SECONDS = 40 * 60

# TTL lock'а парсинга: больше soft_time_limit, чтобы живая задача не потеряла lock
PARSE_LOCK_SECONDS = 45 * 60


@celery_app.task(soft_time_limit=PARSE_SOFT_TIME_LIMIT_SECONDS)
def run_parse_product_task(product_id: int) -> None:
    """
    Celery-задача парсинга продукта.
    Запускается оркестратором, когда продукта ещё нет в БД (строка Product уже создана).

    Шаги:
    0. Redis-lock parse_lock:<product_id>; занят или продукт уже DONE — выходим
    1. fill_status = IN_PROGRESS
    2. Парсит ссылку (сайт ЗЯ → ParsedProduct, картинка в S3)
    3. Записывает спарсенные поля в Product
    4. Все критичные поля есть → DONE, иначе INCOMPLETE
    5. Ошибка парсинга → FAILED + текст в last_error
    6. Подборки продукта из PARSING: DONE → QUEUE + генерация, иначе → FAILED

    :param product_id: ID продукта
    """
    # Lock: одну ссылку парсит только одна задача (повтор от RabbitMQ при acks_late,
    # перезапуск beat-страховкой). Живёт дольше soft_time_limit — если воркер умер,
    # ключ исчезнет сам, и следующий запуск пройдёт.
    with redis_lock(f"parse_lock:{product_id}", expire=PARSE_LOCK_SECONDS) as acquired:
        if not acquired:
            logger.info("[PARSE] Продукт %s уже парсится, пропускаем", product_id)
            return

        with sync_session() as session:
            repository = SyncProductRepository(session)
            product = repository.get_by_id(product_id)

            if not product:
                logger.error("[PARSE] Продукт %s не найден", product_id)
                return

            if product.fill_status == ProductFillStatus.DONE:
                logger.info("[PARSE] Продукт %s уже спарсен, пропускаем", product_id)
                # Подборка могла появиться, когда предыдущая задача уже
                # двинула остальные, — не оставляем её в PARSING
                _continue_selections_after_parse(session, product)
                return

            # Коммитим сразу, чтобы IN_PROGRESS видели остальные соединения
            repository.update(
                product_id, {"fill_status": ProductFillStatus.IN_PROGRESS}
            )
            session.commit()

            logger.info(
                "[PARSE] Парсим продукт %s: %s", product_id, product.product_link
            )
            try:
                # Celery синхронный, парсер async — как с PDF, через asyncio.run
                parsed = asyncio.run(_get_parser().parse(product.product_link))

            except ParserError as exc:
                logger.warning(
                    "[PARSE] Не удалось спарсить product_id=%s: %s: %s",
                    product_id,
                    type(exc).__name__,
                    exc,
                )
                repository.update(
                    product_id,
                    {
                        "fill_status": ProductFillStatus.FAILED,
                        "last_error": f"{type(exc).__name__}: {exc}",
                    },
                )
                session.commit()
                _continue_selections_after_parse(session, product)
                return

            except Exception as exc:
                # Любая другая ошибка — тоже FAILED, иначе продукт навсегда останется IN_PROGRESS
                logger.exception("[PARSE] Неожиданная ошибка product_id=%s", product_id)
                session.rollback()
                repository.update(
                    product_id,
                    {
                        "fill_status": ProductFillStatus.FAILED,
                        "last_error": f"{type(exc).__name__}: {exc}",
                    },
                )
                session.commit()
                _continue_selections_after_parse(session, product)
                return

            product = repository.update(product_id, parsed.to_dict())

            missing = ProductService.missing_fields(product)
            if missing:
                product.fill_status = ProductFillStatus.INCOMPLETE
                product.last_error = "Не хватает полей: " + ", ".join(missing)
                logger.warning(
                    "[PARSE] Продукт %s спарсен не полностью, нет: %s",
                    product_id,
                    missing,
                )
            else:
                product.fill_status = ProductFillStatus.DONE
                product.last_error = None
                logger.info("[PARSE] Продукт %s спарсен", product_id)

            session.commit()

            # Пользователь ждёт подборку, а не парсинг — продолжаем сами
            _continue_selections_after_parse(session, product)


@celery_app.task
def refresh_proxies_task() -> None:
    """
    Периодическая задача (Celery Beat): раз в час берёт свежие прокси
    с freeproxyupdate.com и кладёт список в Redis.

    Сайт не ответил или список пустой — старый список в Redis не трогаем:
    лучше вчерашние прокси, чем никаких.
    """
    try:
        proxies = load_from_site()
    except httpx.HTTPError as exc:
        logger.warning("[PROXY] Сайт со списком прокси не ответил: %s", exc)
        return

    if not proxies:
        logger.warning("[PROXY] Сайт отдал пустой список, старый не трогаем")
        return

    try:
        save_proxies(redis_client, proxies)
    except RedisError as exc:
        logger.error("[PROXY] Redis недоступен, список прокси не сохранён: %s", exc)
        return

    logger.info("[PROXY] Список прокси обновлён: %s шт.", len(proxies))
