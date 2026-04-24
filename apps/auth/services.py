# apps/auth/services.py

# Содержит бизнес-логику: регистрация, подтверждение email,
# логин, обновление токенов.
# Работает через UserRepository — не знает про SQLAlchemy напрямую.

from datetime import timedelta

from apps.auth.schemas import LoginRequest, RegisterRequest
from apps.users.repository import UserRepository
from core.exceptions import (
    EmailNotConfirmedError,
    InvalidCredentialsError,
    InvalidTokenError,
    TokenRevokedError,
    UserAlreadyExistsError,
    UserBannedError,
    UserNotFoundError,
)
from core.security import (
    blacklist_token,
    create_access_token,
    create_confirmation_token,
    create_refresh_token,
    decode_token,
    hash_password_async,
    is_token_blacklisted,
    verify_password_async,
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

    async def register(
            self,
            data: RegisterRequest,
    ) -> dict:
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
            raise UserAlreadyExistsError(f"Email {data.email} уже зарегистрирован")

        # Создаём юзера (email не подтверждён)
        user = await self.repository.create({
            "email": data.email,
            "password": await hash_password_async(data.password),
            "email_confirmed": False,
        }
        )

        # Генерируем токен подтверждения (живёт 24 часа)
        confirmation_token = create_confirmation_token(user_id=user.id)

        # TODO: отправить confirmation_token на почту через aiosmtplib
        # await send_confirmation_email(user.email, confirmation_token)

        await self.repository.session.commit()

        return {
            "message": "Пользователь зарегистрирован. Проверьте почту для подтверждения email.",
            "confirmation_token": confirmation_token,  # убрать после подключения email
        }

    async def confirm_email(
            self,
            token: str,
    ) -> dict:
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
            raise InvalidTokenError("Невалидный или просроченный токен подтверждения")

        # Проверяем, что это именно токен подтверждения email
        if payload.get("type") != "email_confirmation":
            raise InvalidTokenError("Неверный тип токена")

        user_id = int(payload.get("sub"))
        user = await self.repository.get_by_id(user_id)

        if user is None:
            raise UserNotFoundError("Пользователь не найден")

        if user.email_confirmed:
            return {"message": "Email уже подтверждён"}

        # Подтверждаем email
        await self.repository.update(
            user_id,
            {"email_confirmed": True},
        )

        await self.repository.session.commit()

        return {"message": "Email успешно подтверждён. Теперь вы можете войти."}

    async def login(
            self,
            data: LoginRequest,
    ) -> dict:
        """
        Аутентификация пользователя.

        1. Находим юзера по email.
        2. Проверяем пароль.
        3. Проверяем, что email подтверждён.
        4. Генерируем пару токенов (access + refresh).
        """
        user = await self.repository.get_by_email(data.email)

        if user is None:
            raise InvalidCredentialsError("Неверный email или пароль")

        if not await verify_password_async(
                plain_password=data.password,
                hashed_password=user.password,
        ):
            raise InvalidCredentialsError("Неверный email или пароль")

        if not user.email_confirmed:
            raise EmailNotConfirmedError(
                "Email не подтверждён. Проверьте почту."
            )

        if user.is_banned:
            raise UserBannedError("Аккаунт заблокирован")

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

    async def refresh_tokens(
            self,
            refresh_token: str,
    ) -> dict:
        """
        Обновление пары токенов по refresh-токену.

        1. Декодируем refresh-токен.
        2. Проверяем тип (refresh).
        3. Проверяем, что юзер существует и активен.
        4. Генерируем новую пару токенов.
        """
        # не в blacklist ли токен
        if await is_token_blacklisted(refresh_token, "refresh"):
            raise TokenRevokedError("Токен отозван")

        try:
            payload = decode_token(refresh_token)
        except Exception:
            raise InvalidTokenError("Невалидный или просроченный refresh-токен")

        if payload.get("type") != "refresh":
            raise InvalidTokenError("Неверный тип токена")

        user_id = int(payload.get("sub"))
        user = await self.repository.get_by_id(user_id)

        if user is None:
            raise UserNotFoundError("Пользователь не найден")

        if user.is_banned:
            raise UserBannedError("Аккаунт заблокирован")

        # Генерация новой пары
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

    async def logout(
            self,
            access_token: str,
            refresh_token: str,
    ) -> dict:
        """
        Выход из аккаунта.
        Добавляет оба токена в blacklist.
        После этого они не пройдут проверку при обращении к API.
        """
        await blacklist_token(access_token, "access")
        await blacklist_token(refresh_token, "refresh")

        return {"message": "Вы вышли из аккаунта"}
