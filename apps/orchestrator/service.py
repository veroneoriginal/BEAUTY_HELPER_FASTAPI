# apps/orchestrator/service.py

import logging
from urllib.parse import urlsplit

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from apps.balance.repository import BalanceRepository
from apps.balance.services import BalanceService
from apps.parser.exceptions import UnsupportedSite
from apps.parser.registry import strategy_for
from apps.products.models import Product, ProductFillStatus
from apps.products.product_service import ProductService
from apps.products.repository import ProductRepository
from apps.selection.models import SelectionStatus, SelectionTaskType
from apps.selection.repository import SelectionRepository
from apps.selection.services import SelectionService
from apps.users.models import User
from apps.waiting.repository import WaitingRepository
from apps.waiting.services import WaitingService
from infrastructure.celery.tasks import (
    run_create_selection_on_task,
    run_parse_product_task,
)

logger = logging.getLogger(__name__)


def normalize_link(link: str) -> str:
    """
    Приводит ссылку на товар к одному виду: схема + хост + путь.
    Убирает ?utm=…, #… и / на конце, иначе одна карточка даст несколько Product.

    :param link: ссылка, как её прислал пользователь
    :return: чистая ссылка — по ней ищем, её пишем в product_link и отдаём парсеру
    """
    parts = urlsplit(link.strip())
    path = parts.path.rstrip("/")
    return f"{parts.scheme.lower()}://{parts.netloc.lower()}{path}"


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
        logger.warning(
            "[BALANCE] Недостаточно генераций для user_id=%s. "
            "Пополните баланс и отправьте запрос заново.",
            user_id,
        )
        return (
            False,
            "Недостаточно генераций. Пополните баланс, чтобы продолжить.",
        )
    return True, None


async def start_parsing(
    user: User,
    product: Product | None,
    product_link: str,
    task_type: SelectionTaskType,
    product_service: ProductService,
    selection_service: SelectionService,
    balance_service: BalanceService,
    waiting_service: WaitingService,
) -> dict:
    """
    Продукта нет в БД или он не спарсен — запускаем парсинг.

    Создаёт Product (если нет) и подборку в статусе PARSING, резервирует крутку,
    привязывает пользователя, создаёт ожидание и ставит задачу парсинга в Celery.
    Крутка списывается, когда подборка DONE, и возвращается, если FAILED.

    :param user: объект пользователя
    :param product: продукт из БД или None
    :param product_link: чистая ссылка на товар
    :param task_type: тип задачи подборки
    :param product_service: экземпляр ProductService
    :param selection_service: экземпляр SelectionService
    :param balance_service: экземпляр BalanceService
    :param waiting_service: экземпляр WaitingService
    :return: словарь со статусом и сообщением для пользователя
    """
    # Сайт отдал не все критичные поля — повторный парсинг не поможет
    if product and product.fill_status == ProductFillStatus.INCOMPLETE:
        logger.info(
            "[ORCHESTRATOR] Продукт %s спарсен не полностью: %s",
            product.id,
            product.last_error,
        )
        return {
            "status": "error",
            "message": "Не можем разобрать средство по этой ссылке.",
        }

    if not product:
        try:
            product = await product_service.create_product(product_link=product_link)
        except IntegrityError:
            # Ту же ссылку в эту же миллисекунду создал другой запрос (unique на product_link)
            await product_service.repository.session.rollback()
            logger.info(
                "[ORCHESTRATOR] Продукт по ссылке %s уже создаёт другой запрос",
                product_link,
            )
            return {
                "status": "parsing",
                "message": "Средство уже разбираем. Отправьте ссылку ещё раз через минуту.",
            }

    # Резервируем крутку. Нет круток — Product остаётся EMPTY, его
    # распарсит следующий запрос по этой ссылке
    success, error_message = await try_reserve_spin_or_return_message(
        balance_service=balance_service,
        user_id=user.id,
    )
    if not success:
        return {"status": "error", "message": error_message}

    # EMPTY / FAILED / IN_PROGRESS — парсим (заново). Если задача по этому
    # продукту уже идёт, вторая упрётся в parse_lock и выйдет.
    new_selection = await selection_service.create_selection(
        product_id=product.id,
        task_type=task_type,
        status=SelectionStatus.PARSING,
    )
    await selection_service.add_user_to_selection(selection=new_selection, user=user)
    await waiting_service.get_or_create_waiting(
        user_id=user.id,
        selection_id=new_selection.id,
    )

    run_parse_product_task.delay(product_id=product.id)

    logger.info(
        "[ORCHESTRATOR] Парсинг продукта %s (подборка %s) отправлен в Celery",
        product.id,
        new_selection.id,
    )
    return {
        "status": "parsing",
        "message": "Разбираем новое средство. Пришлём подборку, когда будет готово.",
    }


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

    # Чистая ссылка: по ней ищем подборку и продукт
    product_link = normalize_link(product_link)

    # Сайт не поддерживается — отказываем до БД и крутки.
    # Иначе парсер перебрал бы на чужой ссылке все прокси
    try:
        strategy_for(product_link)
    except UnsupportedSite:
        logger.info("[ORCHESTRATOR] Сайт не поддерживается: %s", product_link)
        return {
            "status": "error",
            "message": "Этот сайт пока не поддерживается. Пришлите ссылку "
            "на товар из Золотого Яблока.",
        }

    # Инициализируем сервисы
    selection_service = SelectionService(SelectionRepository(session))
    waiting_service = WaitingService(WaitingRepository(session))
    balance_service = BalanceService(BalanceRepository(session))
    product_service = ProductService(ProductRepository(session))

    # 1. Ищем подборку по ссылке и типу задачи
    selection = await selection_service.get_by_product_and_task_type(
        product_link=product_link,
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

    # 3. Подборка есть, но ещё в процессе (парсинг или генерация)
    if selection and selection.selection_status in (
        SelectionStatus.PARSING,
        SelectionStatus.QUEUE,
        SelectionStatus.PROCESS,
    ):
        # Дубликат запроса (пользователь нажал «получить» несколько раз):
        # если он уже привязан к этой подборке, значит крутка под неё уже
        # зарезервирована — повторно НЕ резервируем. Проверяем именно привязку,
        # а не открытое ожидание: ожидание могло уже закрыться завершившимся
        # прогоном, и тогда повторный резерв осиротел бы навсегда.
        if await selection_service.is_user_attached(
            selection_id=selection.id,
            user_id=user.id,
        ):
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

    # 4.2 Продукта нет или он не спарсен (fill_status не DONE) — в start_parsing:
    # EMPTY / FAILED / IN_PROGRESS парсим (заново), INCOMPLETE — сразу ошибка
    if not product or not product_service.is_filled(product):
        return await start_parsing(
            user=user,
            product=product,
            product_link=product_link,
            task_type=task_type,
            product_service=product_service,
            selection_service=selection_service,
            balance_service=balance_service,
            waiting_service=waiting_service,
        )

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
