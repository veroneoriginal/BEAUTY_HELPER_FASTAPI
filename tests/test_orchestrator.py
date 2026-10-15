# Интеграционные тесты оркестратора get_or_prepare_selection на реальной БД.
# OpenAI/S3/Celery замоканы (run_create_selection_on_task.delay), база — настоящая
# тестовая (beauty_helper_test). Проверяем 4 ветки флоу и движение круток.

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.exc import IntegrityError

from apps.balance.models import UserBalance
from apps.balance.repository import BalanceRepository
from apps.orchestrator import service as orchestrator
from apps.orchestrator.service import get_or_prepare_selection
from apps.products.models import Product, ProductFillStatus
from apps.selection.models import (
    Selection,
    SelectionStatus,
    SelectionTaskType,
    selection_users,
)
from apps.selection.repository import SelectionRepository
from apps.users.models import User
from apps.waiting.repository import WaitingRepository

pytestmark = pytest.mark.integration

TASK_TYPE = SelectionTaskType.COMPOSITION_ANALYSIS


# === Redis для lock'а запроса: в памяти, без сервера ===


class FakeAsyncRedis:
    """
    Async-Redis в памяти: set(nx=True) и delete — всё, что нужно lock'у.
    """

    def __init__(self):
        self.data = {}

    async def set(self, key, value, nx=False, ex=None):
        if nx and key in self.data:
            return None
        self.data[key] = value
        return True

    async def delete(self, key):
        self.data.pop(key, None)


@pytest.fixture(autouse=True)
def fake_redis():
    """
    Оркестратор берёт lock в Redis — в тестах подменяем его памятью.
    """
    redis_client = FakeAsyncRedis()
    with patch.object(orchestrator, "redis_client", redis_client):
        yield redis_client


# === Фабрики тестовых данных ===


async def _make_user(session, email="user@test.com") -> User:
    """
    Создаёт пользователя с минимально необходимыми полями.
    """
    user = User(email=email, password="hash")
    session.add(user)
    await session.flush()
    return user


async def _make_balance(session, user_id, spins=5, reserved=0) -> UserBalance:
    """
    Создаёт строку баланса для пользователя.
    """
    balance = UserBalance(user_id=user_id, spins=spins, reserved_spins=reserved)
    session.add(balance)
    await session.flush()
    return balance


async def _make_product(
    session, link="https://goldapple.ru/p1", fill_status=ProductFillStatus.DONE
) -> Product:
    """
    Создаёт продукт со всеми NOT NULL-полями (по умолчанию спарсенный — DONE).
    """
    product = Product(
        product_link=link,
        name="Крем для лица",
        article="A1",
        product_type="крем",
        product_type_detailed="крем для лица",
        measure_type="объём",
        measure_unit="мл",
        price_rub=Decimal("1990.00"),
        brand="TestBrand",
        fill_status=fill_status,
    )
    session.add(product)
    await session.flush()
    return product


async def _make_selection(session, product_id, status, pdf_url=None) -> Selection:
    """
    Создаёт подборку с заданным статусом.
    """
    selection = Selection(
        product_id=product_id,
        task_type=TASK_TYPE,
        selection_status=status,
        pdf_url=pdf_url,
    )
    session.add(selection)
    await session.flush()
    return selection


# === Ветка 4: parsing (продукта нет в БД или он не спарсен) ===


async def _parsing_selection(session, link):
    """
    Подборка по ссылке после запроса (последняя по id).
    """
    return await SelectionRepository(session).get_by_product_and_task_type(
        product_link=link,
        task_type=TASK_TYPE,
    )


async def test_parsing_branch_when_product_missing(db_session):
    """
    Продукта нет → создаются Product (EMPTY) и подборка PARSING, пользователь
    привязан, задача парсинга в Celery; крутка зарезервирована, ожидание открыто.
    """
    user = await _make_user(db_session)
    await _make_balance(db_session, user.id, spins=5)
    link = "https://goldapple.ru/unknown"

    with patch.object(orchestrator, "run_parse_product_task") as task:
        result = await get_or_prepare_selection(
            user=user,
            product_link=link,
            task_type=TASK_TYPE,
            session=db_session,
        )

    assert result["status"] == "parsing"
    selection = await _parsing_selection(db_session, link)
    assert selection.selection_status == SelectionStatus.PARSING
    assert selection.product.fill_status == ProductFillStatus.EMPTY
    task.delay.assert_called_once_with(product_id=selection.product_id)
    assert await SelectionRepository(db_session).has_user(selection.id, user.id)
    assert (
        await WaitingRepository(db_session).get_open_by_user_and_selection(
            user.id, selection.id
        )
        is not None
    )
    balance = await BalanceRepository(db_session).get_by_user_id(user.id)
    assert (balance.spins, balance.reserved_spins) == (4, 1)


async def test_parsing_branch_when_product_failed(db_session):
    """
    Продукт есть, парсинг упал (FAILED) → парсим заново: подборка PARSING,
    генерация не запускается, крутка зарезервирована.
    """
    user = await _make_user(db_session)
    await _make_balance(db_session, user.id, spins=5)
    product = await _make_product(db_session, fill_status=ProductFillStatus.FAILED)

    with (
        patch.object(orchestrator, "run_parse_product_task") as parse_task,
        patch.object(orchestrator, "run_create_selection_on_task") as task,
    ):
        result = await get_or_prepare_selection(
            user=user,
            product_link=product.product_link,
            task_type=TASK_TYPE,
            session=db_session,
        )

    assert result["status"] == "parsing"
    parse_task.delay.assert_called_once_with(product_id=product.id)
    task.delay.assert_not_called()
    selection = await _parsing_selection(db_session, product.product_link)
    assert selection.selection_status == SelectionStatus.PARSING
    balance = await BalanceRepository(db_session).get_by_user_id(user.id)
    assert (balance.spins, balance.reserved_spins) == (4, 1)


async def test_incomplete_product_not_parsed_again(db_session):
    """
    Продукт INCOMPLETE → «не можем разобрать», ни парсинга, ни подборки.
    """
    user = await _make_user(db_session)
    await _make_balance(db_session, user.id, spins=5)
    product = await _make_product(db_session, fill_status=ProductFillStatus.INCOMPLETE)

    with patch.object(orchestrator, "run_parse_product_task") as parse_task:
        result = await get_or_prepare_selection(
            user=user,
            product_link=product.product_link,
            task_type=TASK_TYPE,
            session=db_session,
        )

    assert result["status"] == "error"
    parse_task.delay.assert_not_called()
    assert await _parsing_selection(db_session, product.product_link) is None


async def test_parsing_duplicate_request_does_not_start_second_task(db_session):
    """
    Тот же пользователь прислал ссылку ещё раз, пока подборка PARSING →
    «уже в работе», вторая задача не ставится, вторая крутка не резервируется.
    """
    user = await _make_user(db_session)
    await _make_balance(db_session, user.id, spins=5)
    link = "https://goldapple.ru/unknown"

    with patch.object(orchestrator, "run_parse_product_task") as parse_task:
        for _ in range(2):
            result = await get_or_prepare_selection(
                user=user,
                product_link=link,
                task_type=TASK_TYPE,
                session=db_session,
            )

    assert result["status"] == "pending"
    parse_task.delay.assert_called_once()
    balance = await BalanceRepository(db_session).get_by_user_id(user.id)
    assert (balance.spins, balance.reserved_spins) == (4, 1)


async def test_parsing_without_spins_returns_error(db_session):
    """
    Новая ссылка, круток нет → ошибка баланса, ни подборки, ни задачи парсинга.
    """
    user = await _make_user(db_session)
    await _make_balance(db_session, user.id, spins=0)
    link = "https://goldapple.ru/unknown"

    with patch.object(orchestrator, "run_parse_product_task") as parse_task:
        result = await get_or_prepare_selection(
            user=user,
            product_link=link,
            task_type=TASK_TYPE,
            session=db_session,
        )

    assert result["status"] == "error"
    parse_task.delay.assert_not_called()
    assert await _parsing_selection(db_session, link) is None


async def test_parsing_race_on_product_create(db_session):
    """
    Тот же Product в эту же миллисекунду создал другой запрос (IntegrityError) →
    «уже разбираем», задача не ставится.
    """
    user = await _make_user(db_session)
    await _make_balance(db_session, user.id, spins=5)

    with (
        patch.object(
            orchestrator.ProductService,
            "create_product",
            side_effect=IntegrityError("insert", {}, Exception("duplicate")),
        ),
        patch.object(orchestrator, "run_parse_product_task") as parse_task,
        # Настоящий rollback откатил бы транзакцию тестовой фикстуры
        patch.object(db_session, "rollback", AsyncMock()) as rollback,
    ):
        result = await get_or_prepare_selection(
            user=user,
            product_link="https://goldapple.ru/unknown",
            task_type=TASK_TYPE,
            session=db_session,
        )

    assert result["status"] == "parsing"
    rollback.assert_awaited_once()
    parse_task.delay.assert_not_called()


# === Ветка created (продукт есть, подборки нет) ===


async def test_created_branch_creates_selection_and_enqueues(db_session):
    """
    Продукт есть, подборки нет → создаётся QUEUE-подборка, ожидание и задача Celery.
    """
    user = await _make_user(db_session)
    await _make_balance(db_session, user.id, spins=3)
    product = await _make_product(db_session)

    with patch.object(orchestrator, "run_create_selection_on_task") as task:
        result = await get_or_prepare_selection(
            user=user,
            product_link=product.product_link,
            task_type=TASK_TYPE,
            session=db_session,
        )

    assert result["status"] == "created"
    task.delay.assert_called_once()

    selection = await SelectionRepository(db_session).get_by_product_and_task_type(
        product_link=product.product_link,
        task_type=TASK_TYPE,
    )
    assert selection is not None
    assert selection.selection_status == SelectionStatus.QUEUE

    # крутка зарезервирована (ушла из доступных в резерв)
    balance = await BalanceRepository(db_session).get_by_user_id(user.id)
    assert (balance.spins, balance.reserved_spins) == (2, 1)

    # пользователь добавлен в ожидание
    waiting = await WaitingRepository(db_session).get_open_by_user_and_selection(
        user_id=user.id,
        selection_id=selection.id,
    )
    assert waiting is not None


async def test_created_branch_failure_midway_commits_nothing(db_session):
    """
    Резерв, подборка, привязка и ожидание — одна транзакция: если упало
    создание ожидания, до этого не было ни одного commit, и get_session
    откатит всё — крутка не останется в резерве без ожидания.
    """
    user = await _make_user(db_session)
    await _make_balance(db_session, user.id, spins=3)
    product = await _make_product(db_session)

    with (
        patch.object(orchestrator, "run_create_selection_on_task") as task,
        patch.object(
            orchestrator.WaitingService,
            "get_or_create_waiting_no_commit",
            AsyncMock(side_effect=RuntimeError("БД упала")),
        ),
        patch.object(db_session, "commit", AsyncMock()) as commit,
        pytest.raises(RuntimeError),
    ):
        await get_or_prepare_selection(
            user=user,
            product_link=product.product_link,
            task_type=TASK_TYPE,
            session=db_session,
        )

    commit.assert_not_awaited()
    task.delay.assert_not_called()


async def test_second_request_while_first_running_does_not_reserve(
    db_session, fake_redis
):
    """
    Lock пары «пользователь + ссылка» занят первым запросом — второй
    сразу отвечает pending: ни подборки, ни резерва крутки.
    """
    user = await _make_user(db_session)
    await _make_balance(db_session, user.id, spins=3)
    product = await _make_product(db_session)
    fake_redis.data[f"selection_request_lock:{user.id}:{product.product_link}"] = "1"

    with patch.object(orchestrator, "run_create_selection_on_task") as task:
        result = await get_or_prepare_selection(
            user=user,
            product_link=product.product_link,
            task_type=TASK_TYPE,
            session=db_session,
        )

    assert result["status"] == "pending"
    task.delay.assert_not_called()

    balance = await BalanceRepository(db_session).get_by_user_id(user.id)
    assert (balance.spins, balance.reserved_spins) == (3, 0)


async def test_lock_released_after_request(db_session, fake_redis):
    """
    После запроса lock снят: следующий запрос того же пользователя
    по той же ссылке пройдёт обычным путём.
    """
    user = await _make_user(db_session)
    await _make_balance(db_session, user.id, spins=3)
    product = await _make_product(db_session)

    with patch.object(orchestrator, "run_create_selection_on_task"):
        await get_or_prepare_selection(
            user=user,
            product_link=product.product_link,
            task_type=TASK_TYPE,
            session=db_session,
        )

    assert fake_redis.data == {}


async def test_redis_down_request_goes_without_lock(db_session, fake_redis):
    """
    Redis недоступен — запрос не отклоняется, идёт без lock'а.
    """
    user = await _make_user(db_session)
    await _make_balance(db_session, user.id, spins=3)
    product = await _make_product(db_session)
    fake_redis.set = AsyncMock(side_effect=ConnectionError("Redis упал"))

    with patch.object(orchestrator, "run_create_selection_on_task") as task:
        result = await get_or_prepare_selection(
            user=user,
            product_link=product.product_link,
            task_type=TASK_TYPE,
            session=db_session,
        )

    assert result["status"] == "created"
    task.delay.assert_called_once()


# === Ветка pending (подборка в процессе) ===


async def test_pending_branch_adds_waiting_and_reserves(db_session):
    """
    Подборка в PROCESS → пользователь в ожидание, крутка зарезервирована.
    """
    user = await _make_user(db_session)
    await _make_balance(db_session, user.id, spins=2)
    product = await _make_product(db_session)
    selection = await _make_selection(db_session, product.id, SelectionStatus.PROCESS)

    result = await get_or_prepare_selection(
        user=user,
        product_link=product.product_link,
        task_type=TASK_TYPE,
        session=db_session,
    )

    assert result["status"] == "pending"

    balance = await BalanceRepository(db_session).get_by_user_id(user.id)
    assert (balance.spins, balance.reserved_spins) == (1, 1)

    waiting = await WaitingRepository(db_session).get_open_by_user_and_selection(
        user_id=user.id,
        selection_id=selection.id,
    )
    assert waiting is not None


async def test_pending_branch_duplicate_click_does_not_reserve_twice(db_session):
    """
    Регрессия: пользователь нажал «получить» несколько раз по одной подборке.
    Он уже привязан к ней (крутка под неё уже забронирована), статус PROCESS —
    повторный запрос НЕ должен резервировать вторую крутку.
    """
    user = await _make_user(db_session)
    await _make_balance(db_session, user.id, spins=2, reserved=1)
    product = await _make_product(db_session)
    selection = await _make_selection(db_session, product.id, SelectionStatus.PROCESS)
    # пользователь уже привязан к подборке (как после первого запроса)
    await db_session.execute(
        selection_users.insert().values(selection_id=selection.id, user_id=user.id)
    )
    await db_session.flush()

    result = await get_or_prepare_selection(
        user=user,
        product_link=product.product_link,
        task_type=TASK_TYPE,
        session=db_session,
    )

    assert result["status"] == "pending"

    # баланс не изменился — вторая крутка не зарезервирована
    balance = await BalanceRepository(db_session).get_by_user_id(user.id)
    assert (balance.spins, balance.reserved_spins) == (2, 1)


# === Ветка done ===


async def test_done_branch_charges_spin_and_returns_pdf(db_session):
    """
    Готовая подборка, пользователь новый → reserve+confirm, отдаётся pdf_url.
    """
    user = await _make_user(db_session)
    await _make_balance(db_session, user.id, spins=2)
    product = await _make_product(db_session)
    selection = await _make_selection(
        db_session,
        product.id,
        SelectionStatus.DONE,
        pdf_url="http://s3/bucket/report.pdf",
    )

    result = await get_or_prepare_selection(
        user=user,
        product_link=product.product_link,
        task_type=TASK_TYPE,
        session=db_session,
    )

    assert result["status"] == "done"
    assert result["pdf_url"] == "http://s3/bucket/report.pdf"

    # reserve → confirm: одна крутка списана, резерв пуст
    balance = await BalanceRepository(db_session).get_by_user_id(user.id)
    assert (balance.spins, balance.reserved_spins) == (1, 0)

    # пользователь привязан к подборке
    has_user = await SelectionRepository(db_session).has_user(selection.id, user.id)
    assert has_user is True


async def test_done_branch_existing_user_not_charged(db_session):
    """
    Готовая подборка уже есть у пользователя → баланс не трогается.
    """
    user = await _make_user(db_session)
    await _make_balance(db_session, user.id, spins=2)
    product = await _make_product(db_session)
    selection = await _make_selection(
        db_session,
        product.id,
        SelectionStatus.DONE,
        pdf_url="http://s3/bucket/report.pdf",
    )
    # пользователь уже привязан к подборке (пишем в промежуточную таблицу напрямую,
    # чтобы не дёргать lazy="selectin"-связь вне async-контекста сервиса)
    await db_session.execute(
        selection_users.insert().values(selection_id=selection.id, user_id=user.id)
    )
    await db_session.flush()

    result = await get_or_prepare_selection(
        user=user,
        product_link=product.product_link,
        task_type=TASK_TYPE,
        session=db_session,
    )

    assert result["status"] == "done"
    balance = await BalanceRepository(db_session).get_by_user_id(user.id)
    assert (balance.spins, balance.reserved_spins) == (2, 0)


# === normalize_link: одна карточка — одна ссылка ===


@pytest.mark.parametrize(
    "link",
    ["https://example.com/123", "goldapple.ru/123", "abc"],
)
async def test_unsupported_site_returns_error(db_session, link):
    """
    Чужой сайт или не ссылка → ошибка сразу: ни продукта,
    ни подборки, ни задачи парсинга, крутка не тронута.
    """
    user = await _make_user(db_session)
    await _make_balance(db_session, user.id, spins=5)

    with patch.object(orchestrator, "run_parse_product_task") as parse_task:
        result = await get_or_prepare_selection(
            user=user,
            product_link=link,
            task_type=TASK_TYPE,
            session=db_session,
        )

    assert result["status"] == "error"
    parse_task.delay.assert_not_called()
    normalized = orchestrator.normalize_link(link)
    assert await _parsing_selection(db_session, normalized) is None
    balance = await BalanceRepository(db_session).get_by_user_id(user.id)
    assert (balance.spins, balance.reserved_spins) == (5, 0)


@pytest.mark.parametrize(
    "link",
    [
        "https://goldapple.ru/19000002015-moisture-surge-100h",
        "https://goldapple.ru/19000002015-moisture-surge-100h/",
        "https://goldapple.ru/19000002015-moisture-surge-100h?utm_source=tg",
        "https://goldapple.ru/19000002015-moisture-surge-100h/?utm=tg#reviews",
        "  HTTPS://GoldApple.ru/19000002015-moisture-surge-100h  ",
    ],
)
def test_normalize_link(link):
    """
    Метки, якорь, / на конце, пробелы и регистр хоста не дают разных ссылок.
    """
    assert (
        orchestrator.normalize_link(link)
        == "https://goldapple.ru/19000002015-moisture-surge-100h"
    )


async def test_dirty_link_finds_existing_product(db_session):
    """
    Ссылка с метками находит продукт, сохранённый по чистой ссылке.
    """
    user = await _make_user(db_session)
    await _make_balance(db_session, user.id, spins=3)
    product = await _make_product(db_session)

    with patch.object(orchestrator, "run_create_selection_on_task"):
        result = await get_or_prepare_selection(
            user=user,
            product_link=product.product_link + "/?utm_source=tg",
            task_type=TASK_TYPE,
            session=db_session,
        )

    assert result["status"] == "created"
