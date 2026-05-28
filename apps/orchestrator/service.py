# apps/orchestrator/service.py

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from apps.balance.repository import BalanceRepository
from apps.balance.services import BalanceService
from apps.products.product_service import ProductService
from apps.products.repository import ProductRepository
from apps.selection.models import SelectionStatus, SelectionTaskType
from apps.selection.repository import SelectionRepository
from apps.selection.services import SelectionService
from apps.users.models import User
from apps.waiting.repository import WaitingRepository
from apps.waiting.services import WaitingService
from infrastructure.celery.tasks import run_create_selection_on_task

logger = logging.getLogger(__name__)


async def try_reserve_spin_or_return_message(
    balance_service,
    user_id: int,
) -> tuple[bool, str | None]:
    """
    Пытается зарезервировать генерацию через BalanceService.
    Если не удалось — возвращает сообщение об ошибке.

    :param balance_service: экземпляр BalanceService
    :param user_id: ID пользователя
    :return: кортеж (успех, сообщение об ошибке или None)
    """
    reserved = await balance_service.reserve_spins(user_id=user_id)
    if not reserved:
        return (
            False,
            "Недостаточно генераций. Пополните баланс, чтобы продолжить.",
        )
    return True, None


async def get_or_prepare_selection(
    user: User,
    product_link: str,
    task_type: SelectionTaskType,
    session: AsyncSession,
) -> dict:
    """
    Главная функция оркестратора.
    Принимает запрос пользователя и управляет всем флоу:

    1. Ищет подборку по ссылке и типу задачи
    2. Если подборка готова (DONE) — сразу отдаёт PDF
    3. Если подборка в процессе — добавляет пользователя в ожидание
    4. Если подборки нет — создаёт продукт, подборку, запускает генерацию

    :param user: объект пользователя
    :param product_link: ссылка на косметический продукт
    :param task_type: тип задачи подборки
    :param session: async сессия SQLAlchemy
    :return: словарь со статусом и сообщением для пользователя
    """

    # Инициализируем сервисы
    selection_service = SelectionService(SelectionRepository(session))
    waiting_service = WaitingService(WaitingRepository(session))
    balance_service = BalanceService(BalanceRepository(session))
    product_service = ProductService(ProductRepository(session))

    # 1. Ищем подборку по ссылке и типу задачи
    selection = await selection_service.get_by_product_and_task_type(
        link_ga=product_link,
        task_type=task_type,
    )

    # 2. Подборка есть и готова (DONE)
    if selection and selection.selection_status == SelectionStatus.DONE:
        # Проверяем есть ли уже у пользователя эта подборка
        ready_response = await selection_service.get_ready_selection_for_user(
            selection=selection,
            user_id=user.id,
        )

        if ready_response:
            logger.info(
                "[ORCHESTRATOR] Пользователь %s уже имеет подборку %s",
                user.id,
                selection.id,
            )
            return {
                "status": "done",
                "message": ready_response,
                "pdf_url": selection.pdf_url,
            }

        # Пользователь новый — резервируем крутку и сразу отдаём PDF
        success, error_message = await try_reserve_spin_or_return_message(
            balance_service=balance_service,
            user_id=user.id,
        )
        if not success:
            return {"status": "error", "message": error_message}

        await selection_service.add_user_to_selection(selection=selection, user=user)
        await balance_service.confirm_spins(user_id=user.id)

        logger.info(
            "[ORCHESTRATOR] Отправляем готовую подборку %s пользователю %s",
            selection.id,
            user.id,
        )
        return {
            "status": "done",
            "message": "Подборка готова! Отправляем PDF.",
            "pdf_url": selection.pdf_url,
        }

    # 3. Подборка есть, но ещё в процессе
    if selection and selection.selection_status in (
        SelectionStatus.QUEUE,
        SelectionStatus.PROCESS,
    ):
        # Проверяем есть ли уже ожидание этого пользователя
        existing_waiting = await waiting_service.get_open_waiting(
            user_id=user.id,
            selection_id=selection.id,
        )
        if existing_waiting:
            return {
                "status": "pending",
                "message": "Подборка уже в работе. Мы пришлём PDF как только будет готово.",
            }

        # Резервируем крутку и добавляем в ожидание
        success, error_message = await try_reserve_spin_or_return_message(
            balance_service=balance_service,
            user_id=user.id,
        )
        if not success:
            return {
                "status": "error",
                "message": error_message,
            }

        await selection_service.add_user_to_selection(selection=selection, user=user)
        await waiting_service.get_or_create_waiting(
            user_id=user.id,
            selection_id=selection.id,
        )

        logger.info(
            "[ORCHESTRATOR] Пользователь %s добавлен в ожидание подборки %s",
            user.id,
            selection.id,
        )
        return {
            "status": "pending",
            "message": "Подборка создаётся. Мы пришлём PDF как только будет готово.",
        }

    # 4. Подборки нет — создаём с нуля
    # 4.1 Ищем продукт в БД
    product = await product_service.get_product_by_link(link=product_link)

    # 4.2 Если продукта нет — заглушка парсера
    if not product:
        logger.info(
            "[ORCHESTRATOR] Продукт не найден для ссылки %s — заглушка парсера",
            product_link,
        )
        return {
            "status": "parsing",
            "message": "Продукт не найден в базе. Запущен парсинг — попробуйте позже.",
        }

    # 4.3 Резервируем крутку
    success, error_message = await try_reserve_spin_or_return_message(
        balance_service=balance_service,
        user_id=user.id,
    )
    if not success:
        return {"status": "error", "message": error_message}

    # 4.4 Создаём подборку
    new_selection = await selection_service.create_selection(
        product_id=product.id,
        task_type=task_type,
    )

    # 4.5 Привязываем пользователя
    await selection_service.add_user_to_selection(
        selection=new_selection,
        user=user,
    )

    # 4.6 Создаём ожидание
    await waiting_service.get_or_create_waiting(
        user_id=user.id,
        selection_id=new_selection.id,
    )

    # 4.7 Запускаем генерацию в Celery
    run_create_selection_on_task.delay(selection_id=new_selection.id)

    logger.info(
        "[ORCHESTRATOR] Создана подборка %s для пользователя %s, задача отправлена в Celery",
        new_selection.id,
        user.id,
    )

    return {
        "status": "created",
        "message": "Анализируем средство. Мы пришлём PDF когда будет готово.",
    }
