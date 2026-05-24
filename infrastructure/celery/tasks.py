# infrastructure/celery/tasks.py

import json
import logging
from contextlib import contextmanager

from redis import Redis

from apps.content_generation.openai.task_processing.main import TaskProcessing
from apps.content_generation.openai.utils.utils_errors import (
    OpenAIInsufficientQuotaError,
)
from apps.orchestrator.encoders import CustomJSONEncoder
from apps.pdf_generation.main import generate_selection_pdf
from apps.pdf_generation.utils import (
    calculate_price_full_request,
    convert_analysis_to_pdf_data,
    convert_json_openai_to_list,
)
from apps.selection.models import Selection, SelectionStatus, SelectionTaskType
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
        pass


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
    from sqlalchemy import select
    from sqlalchemy.orm import joinedload

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
    from dataclasses import asdict

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

    # 7. Сохраняем ссылку на PDF и меняем статус на DONE
    selection.pdf_url = pdf_url
    selection.selection_status = SelectionStatus.DONE
    session.flush()

    logger.info("[Finished] Finished selection_id=%s", selection.id)


def _complete_waitings_for_selection(session, selection: Selection) -> None:
    """
    После завершения подборки находит все открытые ожидания
    и закрывает их — списывает крутку каждому пользователю.

    :param session: синхронная сессия SQLAlchemy
    :param selection: завершённая подборка
    """
    from sqlalchemy import select

    from apps.balance.models import UserBalance

    waitings = session.execute(
        select(Waiting).where(
            Waiting.selection_id == selection.id,
            Waiting.status == WaitingStatus.OPEN,
        )
    ).scalars().all()

    for waiting in waitings:
        # Списываем зарезервированную крутку
        balance = session.execute(
            select(UserBalance).where(UserBalance.user_id == waiting.user_id)
        ).scalar_one_or_none()

        if balance:
            balance.confirm_reserved_spin()
            session.flush()

        # Закрываем ожидание
        waiting.status = WaitingStatus.CLOSED
        session.flush()

        logger.info(
            "[WAITING] Closed waiting_id=%s for user_id=%s",
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
            logger.error("[TASK] Selection %s not found", selection_id)
            return

        # Меняем статус на PROCESS
        selection.selection_status = SelectionStatus.PROCESS
        session.flush()

        try:
            _create_selection_on_task(session=session, selection=selection)
            _complete_waitings_for_selection(session=session, selection=selection)
            session.commit()

            logger.info("[TASK] Selection %s completed successfully", selection_id)

        except OpenAIInsufficientQuotaError:
            logger.critical("❌ На балансе OpenAI закончились деньги")
            selection.selection_status = SelectionStatus.FAILED
            selection.error_message = "Недостаточно средств на балансе OpenAI"
            session.commit()

        except Exception as exc:
            logger.error(
                "[TASK] Failed selection_id=%s error=%s",
                selection_id,
                exc,
            )
            selection.selection_status = SelectionStatus.FAILED
            selection.error_message = str(exc)
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
            logger.info("[WAITING_TASK] Already running, skip")
            return

        with sync_session() as session:
            from sqlalchemy import select
            from sqlalchemy.orm import joinedload

            from apps.balance.models import UserBalance

            waitings = session.execute(
                select(Waiting)
                .options(
                    joinedload(Waiting.selection),
                )
                .where(Waiting.status == WaitingStatus.OPEN)
            ).scalars().all()

            logger.info("[WAITING_TASK] Found %s open waitings", len(waitings))

            for waiting in waitings:
                selection = waiting.selection

                if selection.selection_status == SelectionStatus.DONE:
                    # Списываем крутку
                    balance = session.execute(
                        select(UserBalance).where(
                            UserBalance.user_id == waiting.user_id
                        )
                    ).scalar_one_or_none()

                    if balance:
                        balance.confirm_reserved_spin()
                        session.flush()

                    waiting.status = WaitingStatus.CLOSED
                    session.flush()

                    logger.info(
                        "[WAITING_TASK] Closed waiting_id=%s selection DONE",
                        waiting.id,
                    )

                elif selection.selection_status == SelectionStatus.FAILED:
                    # Возвращаем крутку
                    balance = session.execute(
                        select(UserBalance).where(
                            UserBalance.user_id == waiting.user_id
                        )
                    ).scalar_one_or_none()

                    if balance:
                        balance.release_reserved_spin()
                        session.flush()

                    waiting.status = WaitingStatus.CLOSED
                    session.flush()

                    logger.info(
                        "[WAITING_TASK] Closed waiting_id=%s selection FAILED",
                        waiting.id,
                    )

                elif selection.selection_status == SelectionStatus.QUEUE:
                    # Перезапускаем если задача зависла
                    run_create_selection_on_task.delay(
                        selection_id=selection.id,
                    )
                    logger.info(
                        "[WAITING_TASK] Restarted selection_id=%s",
                        selection.id,
                    )

            session.commit()
