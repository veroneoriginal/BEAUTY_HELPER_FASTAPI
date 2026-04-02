# core/repository.py
# Абстрактный базовый репозиторий.
# Определяет интерфейс (контракт) для работы с данными.
# Сервисы зависят от этого интерфейса, а не от конкретной ORM.
# Если завтра меняем SQLAlchemy на что-то другое —
# переписываем только реализацию, бизнес-логика не трогается.

from abc import ABC, abstractmethod
from typing import Generic, Optional, Sequence, TypeVar

# T — тип модели (User, Product, Selection и т.д.)
# Каждый конкретный репозиторий подставит свою модель.
T = TypeVar("T")


class AbstractRepository(ABC, Generic[T]):
    """
    Базовый интерфейс репозитория.

    Определяет стандартные CRUD-операции.
    Все конкретные репозитории (UserRepository, ProductRepository и т.д.)
    наследуют этот класс и реализуют методы.
    """

    @abstractmethod
    async def get_by_id(self, entity_id: int) -> Optional[T]:
        """Получить запись по ID."""
        raise NotImplementedError

    @abstractmethod
    async def get_all(self) -> Sequence[T]:
        """Получить все записи."""
        raise NotImplementedError

    @abstractmethod
    async def create(self, data: dict) -> T:
        """Создать новую запись."""
        raise NotImplementedError

    @abstractmethod
    async def update(self, entity_id: int, data: dict) -> Optional[T]:
        """Обновить запись по ID."""
        raise NotImplementedError

    @abstractmethod
    async def delete(self, entity_id: int) -> bool:
        """Удалить запись по ID. Возвращает True если удалено."""
        raise NotImplementedError
