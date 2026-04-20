# core/repository/sqlalchemy.py

# SQLAlchemy-реализация базового репозитория.
# Содержит общую логику CRUD, которую наследуют все конкретные репозитории.
# Если меняем ORM — переписываем этот файл, остальное не трогаем.

from typing import Optional, Sequence, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.repository.abstract import AbstractRepository

T = TypeVar("T")


class SQLAlchemyRepository(AbstractRepository[T]):
    """
    Реализация базового репозитория через SQLAlchemy 2.0.

    Каждый конкретный репозиторий (UserRepository и т.д.)
    наследует этот класс и указывает свою модель.
    """

    # Подклассы переопределяют это поле своей моделью
    model: Type[T]

    def __init__(
            self,
            session: AsyncSession,
    ):
        """
        Принимает сессию как зависимость.
        Сессия приходит из FastAPI Depends(get_session).
        """
        self.session = session

    async def get_by_id(
            self,
            entity_id: int,
    ) -> Optional[T]:
        """
        Получить запись по ID.
        """
        return await self.session.get(self.model, entity_id)

    async def get_all(self) -> Sequence[T]:
        """
        Получить все записи.
        """

        result = await self.session.execute(select(self.model))
        return result.scalars().all()

    async def create(
            self,
            data: dict,
    ) -> T:
        """
        Создать новую запись.

        data — словарь с полями модели
        (например, {"email": "...", "password": "..."}).
        """
        instance = self.model(**data)
        self.session.add(instance)
        await self.session.commit()
        await self.session.refresh(instance)
        return instance

    async def update(
            self,
            entity_id: int,
            data: dict,
    ) -> Optional[T]:
        """
        Обновить запись по ID.
        data — словарь с полями для обновления.
        """
        instance = await self.get_by_id(entity_id)
        if instance is None:
            return None

        for key, value in data.items():
            setattr(instance, key, value)

        await self.session.commit()
        await self.session.refresh(instance)
        return instance

    async def delete(
            self,
            entity_id: int,
    ) -> bool:
        """
        Удалить запись по ID. Возвращает True если удалено.
        """
        instance = await self.get_by_id(entity_id)
        if instance is None:
            return False

        await self.session.delete(instance)
        await self.session.commit()
        return True
