# apps/users/services.py

# Бизнес-логика, которая работает через репозиторий.


# Сервисный слой модуля users.
# Содержит бизнес-логику: регистрация, получение профиля, обновление.
# Сервис работает ТОЛЬКО через репозиторий — не знает про SQLAlchemy напрямую.

from typing import Optional, Sequence

from apps.users.models import User
from apps.users.repository import UserRepository
from apps.users.schemas import UserCreate, UserUpdate
from core.exceptions import UserAlreadyExistsError
from core.security import hash_password_async


class UserService:
    """
    Бизнес-логика для работы с пользователями.

    Принимает репозиторий как зависимость.
    Не знает ни про SQLAlchemy, ни про сессии —
    только про интерфейс репозитория.
    """

    def __init__(self, repository: UserRepository):
        self.repository = repository

    async def create_user(self, data: UserCreate) -> User:
        """
        Регистрация нового пользователя.
        Проверяет уникальность email и хеширует пароль.
        """
        # Проверяем, что email не занят
        if await self.repository.exists_by_email(data.email):
            raise UserAlreadyExistsError(f"Email {data.email} уже зарегистрирован")

        # Хешируем пароль перед сохранением
        user_data = {
            "email": data.email,
            "password": await hash_password_async(data.password),
        }

        user = await self.repository.create(user_data)
        await self.repository.session.commit()
        return user

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Получить пользователя по ID."""
        return await self.repository.get_by_id(user_id)

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Получить пользователя по email."""
        return await self.repository.get_by_email(email)

    async def get_all_users(self) -> Sequence[User]:
        """Получить всех пользователей."""
        return await self.repository.get_all()

    async def update_user(
            self,
            user_id: int,
            data: UserUpdate,
    ) -> Optional[User]:
        """
        Обновить профиль пользователя.
        Передаёт только те поля, которые клиент прислал.
        """
        # exclude_unset=True — берём только поля, которые клиент явно передал
        update_data = data.model_dump(exclude_unset=True)

        if not update_data:
            # Клиент не прислал ни одного поля для обновления
            return await self.repository.get_by_id(user_id)

        user = await self.repository.update(user_id, update_data)
        await self.repository.session.commit()
        return user

    async def delete_user(
            self,
            user_id: int,
    ) -> bool:
        """
        Удалить пользователя.
        """

        result = await self.repository.delete(user_id)
        await self.repository.session.commit()
        return result
