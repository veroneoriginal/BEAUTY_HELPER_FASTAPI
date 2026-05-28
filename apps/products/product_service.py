# apps/products/product_service.py


# Сервисный слой модуля products.
# Содержит бизнес-логику: создание продукта, получение, обновление.
# Сервис работает ТОЛЬКО через репозиторий — не знает про SQLAlchemy напрямую.

from typing import Sequence

from apps.products.models import Product, ProductFillStatus
from apps.products.repository import ProductRepository


class ProductService:
    """
    Бизнес-логика для работы с продуктами.

    Принимает репозиторий как зависимость.
    Не знает ни про SQLAlchemy, ни про сессии —
    только про интерфейс репозитория.
    """

    def __init__(self, repository: ProductRepository):
        self.repository = repository

    async def create_product(
        self,
        link_ga: str,
    ) -> Product:
        """
        Создание продукта по ссылке.
        На этом этапе заполняется только ссылка,
        остальные данные придут после парсинга.
        """
        product = await self.repository.create({"link_ga": link_ga})
        await self.repository.session.commit()
        return product

    async def get_product_by_id(self, product_id: int) -> Product | None:
        """Получить продукт по ID."""
        return await self.repository.get_by_id(product_id)

    async def get_product_by_link(self, link: str) -> Product | None:
        """Получить продукт по ссылке из Золотого Яблока."""
        return await self.repository.get_by_link_ga(link)

    async def get_all_products(self) -> Sequence[Product]:
        """Получить все продукты."""
        return await self.repository.get_all()

    async def update_product(
        self,
        product_id: int,
        data: dict,
    ) -> Product | None:
        """
        Обновить данные продукта.
        Используется парсером после парсинга карточки товара.
        """
        product = await self.repository.update(product_id, data)
        await self.repository.session.commit()
        return product

    async def delete_product(self, product_id: int) -> bool:
        """Удалить продукт."""
        result = await self.repository.delete(product_id)
        await self.repository.session.commit()
        return result

    @staticmethod
    def is_filled(product: Product) -> bool:
        """Заполнены ли все данные продукта."""
        return product.fill_status == ProductFillStatus.DONE
