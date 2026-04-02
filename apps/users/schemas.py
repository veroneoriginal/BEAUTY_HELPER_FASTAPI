# apps/users/schemas.py

# Pydantic-схемы для модуля users.
# Определяют формат данных на входе и выходе API.
# Модели БД (SQLAlchemy) и схемы API (Pydantic) — разные вещи.
# Схемы контролируют, какие данные клиент может отправить
# и какие данные он получит в ответ.

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


# === Схемы для создания пользователя ===

class UserCreate(BaseModel):
    """
    Данные для регистрации нового пользователя.
    Приходят от клиента (сайт, Postman).
    """
    email: EmailStr
    password: str


# === Схемы для обновления пользователя ===

class UserUpdate(BaseModel):
    """
    Данные для обновления профиля.
    Все поля опциональные — клиент отправляет только то, что меняет.
    """
    username: Optional[str] = None
    language_code: Optional[str] = None


# === Схемы для ответа клиенту ===

class UserRead(BaseModel):
    """
    Данные пользователя, которые отдаём клиенту.
    Пароль сюда НЕ входит — никогда не отдаём наружу.
    """
    id: int
    email: str
    username: Optional[str] = None
    telegram_id: Optional[int] = None
    language_code: Optional[str] = None
    is_active: bool
    is_banned: bool
    email_confirmed: bool
    created_at: datetime

    model_config = {
        "from_attributes": True,  # позволяет создавать схему прямо из SQLAlchemy-модели
    }
