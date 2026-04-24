# core/security.py

# Модуль безопасности.
# Хеширование паролей (bcrypt) и работа с JWT-токенами.
# Используется сервисами (UserService, AuthService) —
# они вызывают hash_password / verify_password / create_access_token,
# не зная деталей реализации.
import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from core.config import settings
from infrastructure.redis import redis_client

logger = logging.getLogger(__name__)


# === Хеширование паролей ===

def hash_password(password: str) -> str:
    """
    Хеширует пароль через bcrypt.
    Возвращает строку вида '$2b$12$...' — она сохраняется в БД.
    """
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(
        plain_password: str,
        hashed_password: str,
) -> bool:
    """
    Проверяет, совпадает ли введённый пароль с хешем из БД.
    Используется при логине.
    """
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


# === Асинхронные обёртки для bcrypt ===
# bcrypt — CPU-bound, блокирует event loop.
# Выносим в thread pool, чтобы не замораживать async-приложение.


async def hash_password_async(password: str) -> str:
    """
    Асинхронная обёртка над hash_password.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, hash_password, password)


async def verify_password_async(
        plain_password: str,
        hashed_password: str,
) -> bool:
    """Асинхронная обёртка над verify_password."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None, verify_password, plain_password, hashed_password,
    )

# === JWT-токены ===

def create_access_token(
        data: dict,
        expires_delta: timedelta | None = None,
) -> str:
    """
    Создаёт JWT access-токен.

    data — полезная нагрузка (payload), обычно {"sub": user_id}.
    expires_delta — время жизни токена. Если не указано,
    берётся из настроек (ACCESS_TOKEN_EXPIRE_MINUTES).
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    # exp — стандартное поле JWT, по нему библиотека проверяет срок
    to_encode.update({"exp": expire})

    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def create_refresh_token(
        data: dict,
        expires_delta: timedelta | None = None,
) -> str:
    """
    Создаёт JWT refresh-токен (долгоживущий).

    Используется для обновления пары токенов.
    Когда access-токен протухает, клиент отправляет refresh-токен
    и получает новую пару (access + refresh) без повторного логина.

    data — полезная нагрузка (payload), обычно {"sub": user_id}.
    expires_delta — время жизни. По умолчанию REFRESH_TOKEN_EXPIRE_DAYS.
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

    to_encode.update({
        "exp": expire,
        "type": "refresh",  # помечаем тип токена
    })

    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def decode_token(token: str) -> dict:
    """
    Декодирует и проверяет JWT-токен (любой — access или refresh).
    Если токен невалидный или просрочен — выбрасывает исключение.

    Возвращает payload (например, {"sub": 1, "type": "access", "exp": ...}).
    """
    return jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM],
    )


async def is_token_blacklisted(
        token: str,
        token_type: str = "access",
) -> bool:
    """
    Проверяет, находится ли токен в blacklist (Redis).
    Вызывается при каждом защищённом запросе.
    """
    result = await redis_client.get(f"blacklist:{token_type}:{token}")
    return result is not None


async def blacklist_token(
        token: str,
        token_type: str = "access",
) -> None:
    """
    Добавляет токен в blacklist (Redis).
    TTL = оставшееся время жизни токена.
    После этого токен не пройдёт проверку is_token_blacklisted.
    """
    try:
        payload = decode_token(token)
    except Exception as e:
        logger.warning("Токен невалидный или просроченный: %s", e)
        return

    ttl = payload["exp"] - int(time.time())
    if ttl > 0:
        await redis_client.setex(
            f"blacklist:{token_type}:{token}",
            ttl,
            "revoked",
        )

def create_confirmation_token(
        user_id: int,
        expires_delta: timedelta | None = None,
) -> str:
    """
    Создаёт токен подтверждения email.
    Тип 'email_confirmation' зашит внутри — нельзя подменить.
    """
    expire = datetime.now(timezone.utc) + (
            expires_delta or timedelta(hours=24)
    )
    to_encode = {
        "sub": str(user_id),
        "type": "email_confirmation",
        "exp": expire,
    }
    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
