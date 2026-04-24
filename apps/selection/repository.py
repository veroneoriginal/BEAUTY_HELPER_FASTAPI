# apps/selection/repository.py
# Репозиторий подборки.
# Наследует общие CRUD-операции из SQLAlchemyRepository
# и добавляет специфичные методы для работы с подборками.

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from apps.products.models import Product
from apps.selection.models import Selection, SelectionTaskType, selection_users
from apps.users.models import User
from core.repository.sqlalchemy import SQLAlchemyRepository


class SelectionRepository(SQLAlchemyRepository[Selection]):
    """
    Репозиторий для работы с подборками.

    Стандартные методы (get_by_id, get_all, create, update, delete)
    наследуются из SQLAlchemyRepository.

    Здесь — только специфичные запросы для Selection.
    """

    model = Selection

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_product_and_task_type(
            self,
            link_ga: str,
            task_type: str | SelectionTaskType,
    ) -> Selection | None:
        """
        Найти подборку по ссылке на продукт и типу задачи.
        """
        result = await self.session.execute(
            select(Selection)
            .join(Product, Selection.product_id == Product.id)
            .options(joinedload(Selection.product))
            .where(
                Product.link_ga == link_ga,
                Selection.task_type == task_type,
                )
        )
        return result.scalar_one_or_none()

    async def has_user(
            self,
            selection_id: int,
            user_id: int,
    ) -> bool:
        """
        Проверить, привязан ли пользователь к подборке.
        """
        result = await self.session.execute(
            select(selection_users.c.user_id).where(
                selection_users.c.selection_id == selection_id,
                selection_users.c.user_id == user_id,
                )
        )
        return result.scalar_one_or_none() is not None

    async def add_user(
            self,
            selection: Selection,
            user: User,
    ) -> None:
        """
        Привязать пользователя к подборке.
        """
        if not await self.has_user(selection.id, user.id):
            selection.users.append(user)
            await self.session.flush()