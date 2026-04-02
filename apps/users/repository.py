# apps/users/repository.py
# Репозиторий пользователя.
# Наследует общие CRUD-операции из SQLAlchemyRepository
# и добавляет специфичные методы для работы с пользователями.

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.users.models import User
from core.sa_repository import SQLAlchemyRepository


class UserRepository(SQLAlchemyRepository[User]):
    """
    Репозиторий для работы с пользователями.

    Стандартные методы (get_by_id, get_all, create, update, delete)
    наследуются из SQLAlchemyRepository.

    Здесь — только специфичные запросы для User.
    """

    model = User

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_email(self, email: str) -> Optional[User]:
        """Найти пользователя по email (для авторизации)."""
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Найти пользователя по telegram_id (для интеграции с ботом)."""
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def exists_by_email(self, email: str) -> bool:
        """Проверить, занят ли email."""
        user = await self.get_by_email(email)
        return user is not None