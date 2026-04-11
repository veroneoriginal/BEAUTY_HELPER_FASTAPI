# apps/auth/schemas.py

# Pydantic-схемы определяют формат данных для регистрации, логина и токенов.

from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    """
    Данные для регистрации.
    Клиент отправляет email и пароль.
    """
    email: EmailStr
    password: str


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
    password: str


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
