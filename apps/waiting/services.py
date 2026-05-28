# apps/waiting/schemas.py

from apps.waiting.models import Waiting, WaitingStatus
from apps.waiting.repository import WaitingRepository


class WaitingService:
    """
    Бизнес-логика для работы с ожиданиями.
    """

    def __init__(self, repository: WaitingRepository):
        self.repository = repository

    async def get_or_create_waiting(
        self,
        user_id: int,
        selection_id: int,
    ) -> tuple[Waiting, bool]:
        """
        Создаёт или возвращает существующее ожидание для пары (user_id, selection_id).

        :param user_id: ID пользователя
        :param selection_id: ID подборки
        :return: кортеж (объект Waiting, создан ли новый)
        """
        waiting, created = await self.repository.get_or_create(
            user_id=user_id,
            selection_id=selection_id,
        )
        if created:
            await self.repository.session.commit()
        return waiting, created

    async def get_open_waiting(
        self,
        user_id: int,
        selection_id: int,
    ) -> Waiting | None:
        """
        Возвращает открытое ожидание для пары (user_id, selection_id).

        :param user_id: ID пользователя
        :param selection_id: ID подборки
        :return: объект Waiting или None
        """
        return await self.repository.get_open_by_user_and_selection(
            user_id=user_id,
            selection_id=selection_id,
        )

    async def close_waiting(
        self,
        waiting_id: int,
    ) -> Waiting | None:
        """
        Закрывает ожидание — переводит статус в CLOSED.

        :param waiting_id: ID ожидания
        :return: обновлённый объект Waiting
        """
        waiting = await self.repository.update(
            waiting_id,
            {"status": WaitingStatus.CLOSED},
        )
        await self.repository.session.commit()
        return waiting
