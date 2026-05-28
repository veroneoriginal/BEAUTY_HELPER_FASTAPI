# apps/balance/sync_repository.py

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.balance.models import BalanceOperation, BalanceOperationType, UserBalance
from core.repository.sync_sqlalchemy import SyncSQLAlchemyRepository


class SyncBalanceRepository(SyncSQLAlchemyRepository[UserBalance]):
    """
    Синхронный репозиторий баланса для Celery-воркеров.
    Наследует базовые CRUD из SyncSQLAlchemyRepository.
    Работает с psycopg2 через sync_session из core.database.
    """

    model = UserBalance

    def __init__(self, session: Session):
        super().__init__(session)

    def get_by_user_id(self, user_id: int) -> UserBalance | None:
        """
        Получить баланс пользователя без блокировки.

        :param user_id: ID пользователя
        :return: объект UserBalance или None
        """
        result = self.session.execute(
            select(UserBalance).where(UserBalance.user_id == user_id)
        )
        return result.scalar_one_or_none()

    def get_locked_by_user_id(self, user_id: int) -> UserBalance | None:
        """
        Получить баланс с блокировкой строки (SELECT FOR UPDATE).
        Защищает от гонки между воркерами.

        :param user_id: ID пользователя
        :return: объект UserBalance или None
        """
        result = self.session.execute(
            select(UserBalance).where(UserBalance.user_id == user_id).with_for_update()
        )
        return result.scalar_one_or_none()

    def create_operation(
        self,
        user_id: int,
        type_operation: BalanceOperationType,
        count: int,
        balance_after: int,
        description: str = "",
    ) -> BalanceOperation:
        """
        Создать запись в истории операций баланса.

        :param user_id: ID пользователя
        :param type_operation: тип операции
        :param count: количество генераций
        :param balance_after: баланс после операции
        :param description: описание операции
        :return: объект BalanceOperation
        """
        operation = BalanceOperation(
            user_id=user_id,
            type_operation=type_operation,
            count=count,
            balance_after=balance_after,
            description=description,
        )
        self.session.add(operation)
        self.session.flush()
        return operation
