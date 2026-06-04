# apps/auth/schemas.py

# Pydantic-схемы определяют формат данных для регистрации, логина и токенов.

from typing import Annotated

from pydantic import AfterValidator, BaseModel, EmailStr, Field


def _max_72_bytes(value: str) -> str:
    """
    Проверка пароля в байтах.
    bcrypt не принимает пароль длиннее 72 байт.
    (UTF-8): кириллица — 2 байта на символ, эмодзи — до 4.
    """
    if len(value.encode("utf-8")) > 72:
        raise ValueError("Пароль не должен превышать 72 байта")
    return value


# Пароль: 8–128 символов и не больше 72 байт (ограничение bcrypt).
Password = Annotated[
    str,
    Field(min_length=8, max_length=128),
    AfterValidator(_max_72_bytes),
]


class RegisterRequest(BaseModel):
    """
    Данные для регистрации.
    Клиент отправляет email и пароль.
    """

    email: EmailStr
    password: Password


class RegisterResponse(BaseModel):
    """
    Ответ после успешной регистрации.
    В продакшене confirmation_token НЕ возвращается —
    он отправляется на почту. Сейчас возвращаем для тестирования
    через Postman (пока не подключена отправка email).
    """

    message: str
    # TODO: убрать после подключения отправки email
    confirmation_token: str | None = None


class ConfirmEmailResponse(BaseModel):
    """
    Ответ после подтверждения email.
    """

    message: str


class LoginRequest(BaseModel):
    """
    Данные для входа.
    Email + пароль → получаем пару токенов.
    """

    email: EmailStr
    password: Password


class TokenResponse(BaseModel):
    """
    Пара токенов, которую получает клиент после логина.
    access_token — для доступа к API (короткоживущий).
    refresh_token — для обновления пары (долгоживущий).
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """
    Запрос на обновление пары токенов.
    Клиент отправляет refresh_token, получает новую пару.
    """

    refresh_token: str


class LogoutRequest(BaseModel):
    """
    Данные для logout.
    Клиент отправляет оба токена для инвалидации.
    """

    access_token: str
    refresh_token: str


class LogoutResponse(BaseModel):
    """
    Ответ после logout.
    """

    message: str
