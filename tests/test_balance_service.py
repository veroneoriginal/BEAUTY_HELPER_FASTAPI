# tests/test_balance_service.py
# Тесты бизнес-логики баланса с замоканным репозиторием.
# Проверяем арифметику круток (reserve → confirm/release) и ветки нехватки.

from unittest.mock import AsyncMock, MagicMock

import pytest

from apps.balance.models import UserBalance
from apps.balance.services import BalanceService


def make_service(balance):
    """Создаёт BalanceService с замоканным репозиторием, отдающим заданный баланс."""
    repo = MagicMock()
    repo.get_locked_by_user_id = AsyncMock(return_value=balance)
    repo.create_operation = AsyncMock()
    repo.session = MagicMock()
    repo.session.commit = AsyncMock()
    return BalanceService(repo), repo


async def test_reserve_success():
    """Резерв при достаточном балансе: spins-1, reserved+1, запись операции и commit."""
    balance = UserBalance(user_id=1, spins=5, reserved_spins=0)
    service, repo = make_service(balance)

    ok = await service.reserve_spins(user_id=1)

    assert ok is True
    assert balance.spins == 4
    assert balance.reserved_spins == 1
    repo.create_operation.assert_awaited_once()
    repo.session.commit.assert_awaited_once()


async def test_reserve_insufficient():
    """Нехватка круток: резерв не проходит, баланс не меняется, commit не вызывается."""
    balance = UserBalance(user_id=1, spins=0, reserved_spins=0)
    service, repo = make_service(balance)

    ok = await service.reserve_spins(user_id=1)

    assert ok is False
    assert balance.spins == 0
    assert balance.reserved_spins == 0
    repo.create_operation.assert_not_awaited()
    repo.session.commit.assert_not_awaited()


async def test_reserve_no_balance():
    """Если у пользователя нет строки баланса — резерв возвращает False."""
    service, _ = make_service(None)
    assert await service.reserve_spins(user_id=1) is False


async def test_confirm_success():
    """Списание зарезервированной крутки: reserved-1, spins не меняется."""
    balance = UserBalance(user_id=1, spins=4, reserved_spins=1)
    service, _ = make_service(balance)

    ok = await service.confirm_spins(user_id=1)

    assert ok is True
    assert balance.reserved_spins == 0
    assert balance.spins == 4  # списание не возвращает крутку в доступные


async def test_confirm_without_reserve_fails():
    """Списание без резерва (reserved=0) невозможно — False."""
    balance = UserBalance(user_id=1, spins=4, reserved_spins=0)
    service, _ = make_service(balance)
    assert await service.confirm_spins(user_id=1) is False


async def test_release_returns_spin():
    """Возврат из резерва: reserved-1, крутка возвращается в spins."""
    balance = UserBalance(user_id=1, spins=4, reserved_spins=1)
    service, _ = make_service(balance)

    ok = await service.release_spins(user_id=1)

    assert ok is True
    assert balance.reserved_spins == 0
    assert balance.spins == 5  # крутка вернулась в доступные


async def test_release_without_reserve_fails():
    """Возврат без резерва (reserved=0) невозможен — False."""
    balance = UserBalance(user_id=1, spins=4, reserved_spins=0)
    service, _ = make_service(balance)
    assert await service.release_spins(user_id=1) is False


async def test_reserve_then_confirm_flow():
    """Полный успешный цикл: резерв, затем списание; крутка уходит из баланса."""
    balance = UserBalance(user_id=1, spins=2, reserved_spins=0)
    service, _ = make_service(balance)

    assert await service.reserve_spins(user_id=1) is True
    assert (balance.spins, balance.reserved_spins) == (1, 1)
    assert await service.confirm_spins(user_id=1) is True
    assert (balance.spins, balance.reserved_spins) == (1, 0)


@pytest.mark.parametrize("count", [2, 3])
async def test_reserve_multiple(count):
    """Резерв нескольких круток за раз корректно уменьшает spins и растит reserved."""
    balance = UserBalance(user_id=1, spins=5, reserved_spins=0)
    service, _ = make_service(balance)

    ok = await service.reserve_spins(user_id=1, count=count)

    assert ok is True
    assert balance.spins == 5 - count
    assert balance.reserved_spins == count
