# Интеграционные тесты оркестратора get_or_prepare_selection на реальной БД.
# OpenAI/S3/Celery замоканы (run_create_selection_on_task.delay), база — настоящая
# тестовая (beauty_helper_test). Проверяем 4 ветки флоу и движение круток.

from decimal import Decimal
from unittest.mock import patch

import pytest

from apps.balance.models import UserBalance
from apps.balance.repository import BalanceRepository
from apps.orchestrator import service as orchestrator
from apps.orchestrator.service import get_or_prepare_selection
from apps.products.models import Product
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


async def _make_product(session, link="https://gy.ru/p1") -> Product:
    """
    Создаёт продукт со всеми NOT NULL-полями.
    """
    product = Product(
        link_ga=link,
        name="Крем для лица",
        article_ga="A1",
        product_type="крем",
        product_type_detailed="крем для лица",
        measure_type="объём",
        measure_unit="мл",
        price_rub=Decimal("1990.00"),
        brand="TestBrand",
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


# === Ветка 4: parsing (продукта нет в БД) ===


async def test_parsing_branch_when_product_missing(db_session):
    """
    Продукта нет → статус parsing, крутка НЕ резервируется.
    """
    user = await _make_user(db_session)
    await _make_balance(db_session, user.id, spins=5)

    result = await get_or_prepare_selection(
        user=user,
        product_link="https://gy.ru/unknown",
        task_type=TASK_TYPE,
        session=db_session,
    )

    assert result["status"] == "parsing"
    balance = await BalanceRepository(db_session).get_by_user_id(user.id)
    assert (balance.spins, balance.reserved_spins) == (5, 0)


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
            product_link=product.link_ga,
            task_type=TASK_TYPE,
            session=db_session,
        )

    assert result["status"] == "created"
    task.delay.assert_called_once()

    selection = await SelectionRepository(db_session).get_by_product_and_task_type(
        link_ga=product.link_ga,
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
        product_link=product.link_ga,
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
        product_link=product.link_ga,
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
        product_link=product.link_ga,
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
        product_link=product.link_ga,
        task_type=TASK_TYPE,
        session=db_session,
    )

    assert result["status"] == "done"
    balance = await BalanceRepository(db_session).get_by_user_id(user.id)
    assert (balance.spins, balance.reserved_spins) == (2, 0)
