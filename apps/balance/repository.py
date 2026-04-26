# apps/balance/repository.py

# Репозиторий баланса.
# Наследует общие CRUD-операции из SQLAlchemyRepository.
# Работает с обеими моделями: UserBalance и BalanceOperation.
# Ключевая особенность — блокировка строки баланса (select_for_update)
# для защиты от гонки при конкурентных операциях.

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.balance.models import BalanceOperation, BalanceOperationType, UserBalance
from core.repository.sqlalchemy import SQLAlchemyRepository


class BalanceRepository(SQLAlchemyRepository[UserBalance]):
    """
    Репозиторий для работы с балансом пользователя.

    Стандартные методы (get_by_id, get_all, create, update, delete)
    наследуются из SQLAlchemyRepository.

    Здесь — специфичные запросы: получение баланса с блокировкой,
    создание записей в истории операций.
    """

    model = UserBalance

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_user_id(
            self,
            user_id: int,
    ) -> UserBalance | None:
        """
        Получить баланс пользователя (без блокировки).
        Для чтения — просмотр баланса, отображение в UI.
        """
        result = await self.session.execute(
            select(UserBalance).where(UserBalance.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_locked_by_user_id(
            self,
            user_id: int,
    ) -> UserBalance | None:
        """
        Получить баланс пользователя С БЛОКИРОВКОЙ строки.

        Аналог Django select_for_update().
        Используется при любых изменениях баланса —
        защищает от гонки при конкурентных запросах.
        Должен вызываться внутри транзакции (до commit).
        """
        result = await self.session.execute(
            select(UserBalance)
            .where(UserBalance.user_id == user_id)
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def create_operation(
            self,
            user_id: int,
            type_operation: BalanceOperationType,
            count: int,
            balance_after: int,
            description: str = "",
    ) -> BalanceOperation:
        """
        Создать запись в истории операций.
        Вызывается из сервиса после каждого изменения баланса.
        """
        operation = BalanceOperation(
            user_id=user_id,
            type_operation=type_operation,
            count=count,
            balance_after=balance_after,
            description=description,
        )
        self.session.add(operation)
        await self.session.flush()
        await self.session.refresh(operation)
        return operation

    async def get_operations_by_user_id(
            self,
            user_id: int,
    ) -> list[BalanceOperation]:
        """
        Получить историю операций пользователя.
        Сортировка — от новых к старым.
        """
        result = await self.session.execute(
            select(BalanceOperation)
            .where(BalanceOperation.user_id == user_id)
            .order_by(BalanceOperation.created_at.desc())
        )
        return list(result.scalars().all())
