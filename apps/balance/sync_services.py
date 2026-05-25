# apps/balance/sync_services.py

from apps.balance.models import BalanceOperationType
from apps.balance.sync_repository import SyncBalanceRepository


class SyncBalanceService:
    """
    Синхронный сервис баланса для Celery-воркеров.
    Зеркало BalanceService но без async/await.
    Работает с SyncBalanceRepository через psycopg2.
    """

    def __init__(self, repository: SyncBalanceRepository):
        self.repository = repository

    def confirm_spins(
            self,
            user_id: int,
            count: int = 1,
            description: str = "Списание генераций после завершения анализа",
    ) -> bool:
        """
        Списать зарезервированные генерации после успешного анализа.
        Уменьшает reserved_spins.

        :param user_id: ID пользователя
        :param count: количество генераций
        :param description: описание операции
        :return: True если успешно, False если баланс не найден
        """
        balance = self.repository.get_locked_by_user_id(user_id)
        if balance is None:
            return False

        balance.reserved_spins -= count

        self.repository.create_operation(
            user_id=user_id,
            type_operation=BalanceOperationType.CONFIRM,
            count=count,
            balance_after=balance.spins,
            description=description,
        )

        return True

    def release_spins(
            self,
            user_id: int,
            count: int = 1,
            description: str = "Возврат генераций из резерва (анализ завершился с ошибкой)",
    ) -> bool:
        """
        Вернуть зарезервированные генерации обратно в доступные.
        Вызывается если анализ завершился ошибкой.

        :param user_id: ID пользователя
        :param count: количество генераций
        :param description: описание операции
        :return: True если успешно, False если баланс не найден
        """
        balance = self.repository.get_locked_by_user_id(user_id)
        if balance is None:
            return False

        balance.reserved_spins -= count
        balance.spins += count

        self.repository.create_operation(
            user_id=user_id,
            type_operation=BalanceOperationType.RELEASE,
            count=count,
            balance_after=balance.spins,
            description=description,
        )

        return True