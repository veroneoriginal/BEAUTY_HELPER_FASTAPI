# apps/products/sync_repository.py

from sqlalchemy.orm import Session

from apps.products.models import Product
from core.repository.sync_sqlalchemy import SyncSQLAlchemyRepository


class SyncProductRepository(SyncSQLAlchemyRepository[Product]):
    """
    Синхронный репозиторий продукта для Celery-воркеров (задача парсинга).
    Наследует базовые CRUD из SyncSQLAlchemyRepository.
    Работает с psycopg2 через sync_session из core.database.
    """

    model = Product

    def __init__(self, session: Session):
        super().__init__(session)
