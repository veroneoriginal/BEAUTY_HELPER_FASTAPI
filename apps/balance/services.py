# apps/balance/services.py

# Сервисный слой модуля balance.
# Содержит бизнес-логику: пополнение, резервирование, списание, возврат.
# Каждая операция блокирует строку баланса (select_for_update)
# и записывает историю в BalanceOperation.
# Сервис работает ТОЛЬКО через репозиторий — не знает про SQLAlchemy напрямую.

from apps.balance.models import BalanceOperationType, UserBalance
from apps.balance.repository import BalanceRepository


class BalanceService:
    """
    Бизнес-логика для работы с балансом пользователя.

    Принимает репозиторий как зависимость.
    Все операции, изменяющие баланс:
    1. Блокируют строку (get_locked_by_user_id).
    2. Изменяют поля.
    3. Записывают операцию в историю.
    4. Делают commit.
    """

    def __init__(self, repository: BalanceRepository):
        self.repository = repository

    # === Создание баланса ===

    async def create_balance_no_commit(
            self,
            user_id: int,
    ) -> UserBalance:
        """
        Создать баланс без commit.
        Используется когда баланс создаётся в составе
        другой транзакции (например, при регистрации).
        Commit делает вызывающий код.
        """
        balance = await self.repository.create({
            "user_id": user_id,
            "spins": 0,
            "reserved_spins": 0,
        })
        return balance

    # === Чтение ===

    async def get_balance(
            self,
            user_id: int,
    ) -> UserBalance | None:
        """
        Получить баланс пользователя (без блокировки).
        Для отображения в UI.
        """
        return await self.repository.get_by_user_id(user_id)

    async def get_operations(
            self,
            user_id: int,
    ) -> list:
        """
        Получить историю операций пользователя.
        """
        return await self.repository.get_operations_by_user_id(user_id)

    # === Пополнение ===

    async def add_spins_no_commit(
            self,
            user_id: int,
            count: int,
            description: str = "Начисление генераций",
    ) -> bool:
        """
        Пополнить баланс без commit.
        Используется когда начисление идёт в составе
        другой транзакции (например, выдача пакета).
        Commit делает вызывающий код.
        """
        balance = await self.repository.get_locked_by_user_id(user_id)
        if balance is None:
            return False

        balance.spins += count

        await self.repository.create_operation(
            user_id=user_id,
            type_operation=BalanceOperationType.ADD,
            count=count,
            balance_after=balance.spins,
            description=description,
        )

        return True

    # === Резервирование ===

    async def reserve_spins(
            self,
            user_id: int,
            count: int = 1,
            description: str = "Резервирование генераций перед запуском анализа",
    ) -> bool:
        """
        Резервировать генерации перед запуском анализа.

        Уменьшает доступные (spins), увеличивает зарезервированные (reserved_spins).
        Возвращает False если на балансе недостаточно генераций.
        """
        balance = await self.repository.get_locked_by_user_id(user_id)
        if balance is None:
            return False

        if balance.spins < count:
            return False

        balance.spins -= count
        balance.reserved_spins += count

        await self.repository.create_operation(
            user_id=user_id,
            type_operation=BalanceOperationType.RESERVE,
            count=count,
            balance_after=balance.spins,
            description=description,
        )

        await self.repository.session.commit()
        return True

    # === Списание ===

    async def confirm_spins(
            self,
            user_id: int,
            count: int = 1,
            description: str = "Списание генераций после завершения анализа",
    ) -> bool:
        """
        Списать зарезервированные генерации.

        Вызывается после успешного завершения анализа.
        Уменьшает reserved_spins — генерация использована.
        """
        balance = await self.repository.get_locked_by_user_id(user_id)
        if balance is None:
            return False

        balance.reserved_spins -= count

        await self.repository.create_operation(
            user_id=user_id,
            type_operation=BalanceOperationType.CONFIRM,
            count=count,
            balance_after=balance.spins,
            description=description,
        )

        await self.repository.session.commit()
        return True

    # === Возврат ===

    async def release_spins(
            self,
            user_id: int,
            count: int = 1,
            description: str = "Возврат генераций из резерва (анализ завершился с ошибкой)",
    ) -> bool:
        """
        Вернуть зарезервированные генерации обратно в доступные.

        Вызывается если анализ завершился ошибкой —
        генерация не потрачена, нужно вернуть попытку.
        """
        balance = await self.repository.get_locked_by_user_id(user_id)
        if balance is None:
            return False

        balance.reserved_spins -= count
        balance.spins += count

        await self.repository.create_operation(
            user_id=user_id,
            type_operation=BalanceOperationType.RELEASE,
            count=count,
            balance_after=balance.spins,
            description=description,
        )

        await self.repository.session.commit()
        return True
