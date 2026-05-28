# apps/waiting/repository.py

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.waiting.models import Waiting, WaitingStatus
from core.repository.sqlalchemy import SQLAlchemyRepository


class WaitingRepository(SQLAlchemyRepository[Waiting]):
    """
    Репозиторий для работы с ожиданиями.
    """

    model = Waiting

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_open_by_user_and_selection(
        self,
        user_id: int,
        selection_id: int,
    ) -> Waiting | None:
        """
        Возвращает открытое ожидание для пары (user_id, selection_id).

        :param user_id: ID пользователя
        :param selection_id: ID подборки
        :return: объект Waiting со статусом OPEN или None
        """
        result = await self.session.execute(
            select(Waiting).where(
                Waiting.user_id == user_id,
                Waiting.selection_id == selection_id,
                Waiting.status == WaitingStatus.OPEN,
            )
        )
        return result.scalar_one_or_none()

    async def get_or_create(
        self,
        user_id: int,
        selection_id: int,
    ) -> tuple[Waiting, bool]:
        """
        Возвращает существующее ожидание или создаёт новое.

        :param user_id: ID пользователя
        :param selection_id: ID подборки
        :return: кортеж (объект Waiting, создан ли новый)
        """
        result = await self.session.execute(
            select(Waiting).where(
                Waiting.user_id == user_id,
                Waiting.selection_id == selection_id,
            )
        )
        waiting = result.scalar_one_or_none()

        if waiting:
            return waiting, False

        waiting = await self.create(
            {
                "user_id": user_id,
                "selection_id": selection_id,
                "status": WaitingStatus.OPEN,
            }
        )
        return waiting, True
