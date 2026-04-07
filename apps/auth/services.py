# apps/auth/services.py

# Содержит бизнес-логику: регистрация, подтверждение email,
# логин, обновление токенов.
# Работает через UserRepository — не знает про SQLAlchemy напрямую.

from datetime import timedelta

from apps.users.repository import UserRepository
from apps.auth.schemas import RegisterRequest, LoginRequest
from core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)


class AuthService:
    """
    Бизнес-логика аутентификации.

    Принимает UserRepository как зависимость.
    Отвечает за:
    - регистрацию (создание юзера + генерация токена подтверждения)
    - подтверждение email
    - логин (проверка пароля + выдача токенов)
    - обновление пары токенов по refresh-токену
    """

    def __init__(self, repository: UserRepository):
        self.repository = repository

    async def register(self, data: RegisterRequest) -> dict:
        """
        Регистрация нового пользователя.

        1. Проверяем, что email не занят.
        2. Хешируем пароль.
        3. Создаём юзера с email_confirmed=False.
        4. Генерируем токен подтверждения email.
        5. Возвращаем сообщение (+ токен для тестирования).

        В продакшене токен отправляется на почту,
        а не возвращается в ответе API.
        """
        # Проверяем уникальность email
        if await self.repository.exists_by_email(data.email):
            raise ValueError(f"Email {data.email} уже зарегистрирован")

        # Создаём юзера (email не подтверждён)
        user = await self.repository.create({
            "email": data.email,
            "password": hash_password(data.password),
            "email_confirmed": False,
        })

        # Генерируем токен подтверждения (живёт 24 часа)
        confirmation_token = create_access_token(
            data={"sub": str(user.id), "type": "email_confirmation"},
            expires_delta=timedelta(hours=24),
        )

        # TODO: отправить confirmation_token на почту через aiosmtplib
        # await send_confirmation_email(user.email, confirmation_token)

        return {
            "message": "Пользователь зарегистрирован. Проверьте почту для подтверждения email.",
            "confirmation_token": confirmation_token,  # убрать после подключения email
        }

    async def confirm_email(self, token: str) -> dict:
        """
        Подтверждение email по токену из ссылки.

        1. Декодируем токен.
        2. Проверяем тип токена (email_confirmation).
        3. Находим юзера по ID из payload.
        4. Ставим email_confirmed=True.
        """
        try:
            payload = decode_token(token)
        except Exception:
            raise ValueError("Невалидный или просроченный токен подтверждения")

        # Проверяем, что это именно токен подтверждения email
        if payload.get("type") != "email_confirmation":
            raise ValueError("Неверный тип токена")

        user_id = int(payload.get("sub"))
        user = await self.repository.get_by_id(user_id)

        if user is None:
            raise ValueError("Пользователь не найден")

        if user.email_confirmed:
            return {"message": "Email уже подтверждён"}

        # Подтверждаем email
        await self.repository.update(user_id, {"email_confirmed": True})

        return {"message": "Email успешно подтверждён. Теперь вы можете войти."}

    async def login(self, data: LoginRequest) -> dict:
        """
        Аутентификация пользователя.

        1. Находим юзера по email.
        2. Проверяем пароль.
        3. Проверяем, что email подтверждён.
        4. Генерируем пару токенов (access + refresh).
        """
        user = await self.repository.get_by_email(data.email)

        if user is None:
            raise ValueError("Неверный email или пароль")

        if not verify_password(data.password, user.password):
            raise ValueError("Неверный email или пароль")

        if not user.email_confirmed:
            raise ValueError(
                "Email не подтверждён. Проверьте почту."
            )

        if user.is_banned:
            raise ValueError("Аккаунт заблокирован")

        # Генерируем пару токенов
        access_token = create_access_token(
            data={"sub": str(user.id)},
        )
        refresh_token = create_refresh_token(
            data={"sub": str(user.id)},
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }


    async def refresh_tokens(self, refresh_token: str) -> dict:
        """
        Обновление пары токенов по refresh-токену.

        1. Декодируем refresh-токен.
        2. Проверяем тип (refresh).
        3. Проверяем, что юзер существует и активен.
        4. Генерируем новую пару токенов.
        """
        try:
            payload = decode_token(refresh_token)
        except Exception:
            raise ValueError("Невалидный или просроченный refresh-токен")

        if payload.get("type") != "refresh":
            raise ValueError("Неверный тип токена")

        user_id = int(payload.get("sub"))
        user = await self.repository.get_by_id(user_id)

        if user is None:
            raise ValueError("Пользователь не найден")

        if user.is_banned:
            raise ValueError("Аккаунт заблокирован")

        # Генерируем новую пару
        new_access = create_access_token(
            data={"sub": str(user.id)},
        )
        new_refresh = create_refresh_token(
            data={"sub": str(user.id)},
        )

        return {
            "access_token": new_access,
            "refresh_token": new_refresh,
            "token_type": "bearer",
        }
