# core/repository/sync_sqlalchemy.py

from typing import Optional, Sequence, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

T = TypeVar("T")


class SyncSQLAlchemyRepository:
    """
    Синхронная реализация базового репозитория через SQLAlchemy 2.0.
    Используется в Celery-воркерах где нет event loop.

    Зеркало SQLAlchemyRepository но без async/await.
    Работает с psycopg2 через sync_session из core.database.
    """

    model: Type[T]

    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, entity_id: int) -> Optional[T]:
        """
        Получить запись по ID.
        """
        return self.session.get(self.model, entity_id)

    def get_all(self) -> Sequence[T]:
        """
        Получить все записи.
        """
        result = self.session.execute(select(self.model))
        return result.scalars().all()

    def create(self, data: dict) -> T:
        """
        Создать новую запись.
        """
        instance = self.model(**data)
        self.session.add(instance)
        self.session.flush()
        self.session.refresh(instance)
        return instance

    def update(self, entity_id: int, data: dict) -> Optional[T]:
        """
        Обновить запись по ID.
        """
        instance = self.get_by_id(entity_id)
        if instance is None:
            return None

        for key, value in data.items():
            setattr(instance, key, value)
        self.session.flush()
        self.session.refresh(instance)
        return instance

    def delete(self, entity_id: int) -> bool:
        """
        Удалить запись по ID.
        """
        instance = self.get_by_id(entity_id)
        if instance is None:
            return False

        self.session.delete(instance)
        self.session.flush()
        return True
