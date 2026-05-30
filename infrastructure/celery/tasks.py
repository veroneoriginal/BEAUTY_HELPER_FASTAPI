# infrastructure/celery/tasks.py

import json
import logging
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timezone

from redis import Redis
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from apps.balance.models import BalanceOperation, UserBalance  # noqa: F401
from apps.balance.sync_repository import SyncBalanceRepository
from apps.balance.sync_services import SyncBalanceService
from apps.content_generation.openai.task_processing.main import TaskProcessing
from apps.content_generation.openai.utils.utils_errors import (
    OpenAIInsufficientQuotaError,
)
from apps.orchestrator.encoders import CustomJSONEncoder
from apps.package.models import Package, UserPackage  # noqa: F401
from apps.pdf_generation.main import generate_selection_pdf
from apps.pdf_generation.utils import (
    calculate_price_full_request,
    convert_analysis_to_pdf_data,
    convert_json_openai_to_list,
)
from apps.products.models import Product  # noqa: F401
from apps.selection.models import Selection, SelectionStatus, SelectionTaskType
from apps.users.models import User  # noqa: F401
from apps.waiting.models import Waiting, WaitingStatus
from core.config import settings
from core.database import sync_session
from infrastructure.celery.app import celery_app

logger = logging.getLogger(__name__)

redis_client = Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD,
    db=0,
)


@contextmanager
def redis_lock(lock_name: str, expire: int = 55):
    """
    Контекстный менеджер для блокировки повторного запуска задачи через Redis.
    Устанавливает ключ в Redis на время выполнения задачи.

    :param lock_name: имя блокировки — ключ в Redis
    :param expire: время жизни блокировки в секундах
    """

    # Установка ключа в Redis с условием.
    lock_acquired = redis_client.set(lock_name, "locked", ex=expire, nx=True)
    try:
        yield lock_acquired
    finally:
        if lock_acquired:
            redis_client.delete(lock_name)


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


def _create_selection_on_task(session, selection: Selection) -> None:
    """
    Основная логика генерации подборки:
    1. Получает DTO продукта
    2. Отправляет запрос в OpenAI (пошагово)
    3. Сохраняет запросы и ответы в подборку
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

    # 2. Запускаем анализ через OpenAI
    work_task_processing = TaskProcessing(
        collection_data=dto,
        task_type=SelectionTaskType(selection.task_type),
    )

    logger.info("[OPENAI] Run task processing")
    work_task_processing.run_task_processing()

    # 3. Сохраняем запросы в OpenAI
    selection.request_details = json.dumps(
        work_task_processing.request_data,
        ensure_ascii=False,
        indent=2,
    )

    # 4. Сохраняем ответы от OpenAI
    selection.final_analysis = json.dumps(
        work_task_processing.response_data,
        ensure_ascii=False,
        indent=2,
        cls=CustomJSONEncoder,
    )
    session.flush()

    logger.info("[OPENAI] Saved request and response to selection")

    # 5. Считаем стоимость
    if not selection.final_analysis:
        raise ValueError("final_analysis пустой — OpenAI не вернул ответ")

    answer_from_openai = convert_json_openai_to_list(
        analysis_data=selection.final_analysis,
    )
    price_request = calculate_price_full_request(
        answer_from_openai=answer_from_openai,
    )
    selection.price = price_request
    session.flush()

    logger.info("[PRICE] price_request=%s", price_request)

    # 6. Генерируем PDF
    analys_to_pdf = convert_analysis_to_pdf_data(
        answer_from_openai=answer_from_openai,
    )
    pdf_url = generate_selection_pdf(
        task_type=SelectionTaskType(selection.task_type),
        product_data=dto,
        analys=analys_to_pdf,
    )

    logger.info("[PDF] Generated pdf_url=%s", pdf_url)

    if not pdf_url:
        raise RuntimeError("PDF не был загружен на S3 — pdf_url пустой")

    # 7. Сохраняем ссылку на PDF и меняем статус на DONE
    selection.pdf_url = pdf_url
    selection.selection_status = SelectionStatus.DONE
    session.flush()

    logger.info("[Finished] Finished selection_id=%s", selection.id)


def _complete_waitings_for_selection(session, selection: Selection) -> None:
    """
    После завершения создания подборки находит все открытые ожидания
    и закрывает их — списывает крутку каждому пользователю.

    :param session: синхронная сессия SQLAlchemy
    :param selection: завершённая подборка
    """

    balance_service = SyncBalanceService(SyncBalanceRepository(session))

    waitings = (
        session.execute(
            select(Waiting).where(
                Waiting.selection_id == selection.id,
                Waiting.status == WaitingStatus.OPEN,
            )
        )
        .scalars()
        .all()
    )

    for waiting in waitings:
        # Списываем зарезервированную крутку
        balance_service.confirm_spins(user_id=waiting.user_id)

        # Закрываем ожидание
        waiting.status = WaitingStatus.CLOSED
        session.flush()

        logger.info(
            "[WAITING] Закрыто ожидание waiting_id=%s для user_id=%s",
            waiting.id,
            waiting.user_id,
        )


def _release_spins_for_selection(session, selection_id: int) -> None:
    """
    При финальном фейле задачи снимает резерв крутки
    для всех пользователей с открытыми ожиданиями.
    """
    balance_service = SyncBalanceService(SyncBalanceRepository(session))

    waitings = (
        session.execute(
            select(Waiting).where(
                Waiting.selection_id == selection_id,
                Waiting.status == WaitingStatus.OPEN,
            )
        )
        .scalars()
        .all()
    )

    for waiting in waitings:
        balance_service.release_spins(user_id=waiting.user_id)
        waiting.status = WaitingStatus.CLOSED
        session.flush()
        logger.info(
            "[WAITING] Возвращена крутка waiting_id=%s для user_id=%s",
            waiting.id,
            waiting.user_id,
        )


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
    with sync_session() as session:
        selection = _get_selection_with_product(session, selection_id)

        if not selection:
            logger.error("[TASK] Подборка %s не найдена", selection_id)
            return

        # Меняем статус на PROCESS
        selection.selection_status = SelectionStatus.PROCESS
        session.flush()

        try:
            _create_selection_on_task(session=session, selection=selection)
            _complete_waitings_for_selection(session=session, selection=selection)
            session.commit()

            logger.info("[TASK] Подборка %s успешно завершена", selection_id)

        except OpenAIInsufficientQuotaError:
            logger.critical("❌ На балансе OpenAI закончились деньги")
            session.rollback()
            selection = _get_selection_with_product(session, selection_id)
            selection.selection_status = SelectionStatus.FAILED
            selection.error_message = "Недостаточно средств на балансе OpenAI"
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


@celery_app.task
def run_waiting_task() -> None:
    """
    Периодическая задача (Celery Beat) — страховочная проверка.
    Запускается каждые 30 секунд.

    Находит все открытые ожидания и действует по статусу подборки:
    - DONE → списывает крутку, закрывает ожидание
    - FAILED → возвращает крутку, закрывает ожидание
    - QUEUE/PROCESS → перезапускает генерацию если зависла
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
                    # Списываем крутку
                    balance_service.confirm_spins(user_id=waiting.user_id)

                    waiting.status = WaitingStatus.CLOSED
                    session.flush()

                    logger.info(
                        "[WAITING_TASK] Закрыто ожидание %s, статус подборки - DONE",
                        waiting.id,
                    )

                elif selection.selection_status == SelectionStatus.FAILED:
                    # Возвращаем крутку
                    balance_service.release_spins(user_id=waiting.user_id)

                    waiting.status = WaitingStatus.CLOSED
                    session.flush()

                    logger.info(
                        "[WAITING_TASK] Закрыто ожидание %s, статус подборки - FAILED",
                        waiting.id,
                    )

                elif selection.selection_status == SelectionStatus.QUEUE:
                    age_seconds = (
                        datetime.now(timezone.utc) - selection.created_at
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

            session.commit()
