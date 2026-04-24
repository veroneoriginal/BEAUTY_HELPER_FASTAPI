# Репозиторий продукта.
# Наследует общие CRUD-операции из SQLAlchemyRepository
# и добавляет специфичные методы для работы с продуктами.

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.products.models import Product
from core.repository.sqlalchemy import SQLAlchemyRepository


class ProductRepository(SQLAlchemyRepository[Product]):
    """
    Репозиторий для работы с продуктами.

    Стандартные методы (get_by_id, get_all, create, update, delete)
    наследуются из SQLAlchemyRepository.

    Здесь — только специфичные запросы для Product.
    """

    model = Product

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_link_ga(
            self,
            link: str,
    ) -> Product | None:
        """
        Найти продукт по ссылке из Золотого Яблока.
        """
        result = await self.session.execute(
            select(self.model).where(self.model.link_ga == link)
        )
        return result.scalar_one_or_none()