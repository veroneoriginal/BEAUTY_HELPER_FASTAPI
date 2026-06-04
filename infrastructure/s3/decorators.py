# infrastructure/s3/decorators.py
import asyncio
import logging
from functools import wraps

from botocore.exceptions import BotoCoreError, ClientError, EndpointConnectionError

logger = logging.getLogger(__name__)

# Сетевые/транзиентные ошибки S3, которые имеет смысл повторить.
S3_RETRYABLE = (EndpointConnectionError, ClientError, BotoCoreError)
S3_MAX_ATTEMPTS = 3
S3_BACKOFF_BASE = 0.5  # секунды; задержка растёт экспоненциально: 0.5, 1.0, ...


def s3_safe_call(func):
    """
    Асинхронный декоратор для методов S3Service.

    - Повторяет вызов при транзиентных ошибках S3 (до S3_MAX_ATTEMPTS раз)
      с экспоненциальным бэкоффом, логируя каждую неудачную попытку.
    - Если все попытки исчерпаны или ошибка неизвестна — возвращает
      стандартный словарь с error вместо выброса исключения.

    Подходит для методов, возвращающих dict с ключами:
    - status_code: HTTP-статус ответа от S3
    - etag: идентификатор версии объекта
    - error: None если успех, иначе строка с описанием ошибки
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        last_exc = None
        for attempt in range(1, S3_MAX_ATTEMPTS + 1):
            try:
                return await func(*args, **kwargs)
            except S3_RETRYABLE as e:
                last_exc = e
                if attempt < S3_MAX_ATTEMPTS:
                    delay = S3_BACKOFF_BASE * (2 ** (attempt - 1))
                    logger.warning(
                        "[S3] %s: попытка %s/%s не удалась (%s), повтор через %.1f с",
                        func.__name__,
                        attempt,
                        S3_MAX_ATTEMPTS,
                        e,
                        delay,
                    )
                    await asyncio.sleep(delay)
            except Exception as e:
                logger.error("[S3] %s: неизвестная ошибка: %s", func.__name__, e)
                return {
                    "status_code": None,
                    "etag": None,
                    "error": f"Неизвестная ошибка: {e}",
                }

        logger.error(
            "[S3] %s: все %s попыток исчерпаны: %s",
            func.__name__,
            S3_MAX_ATTEMPTS,
            last_exc,
        )
        return {
            "status_code": None,
            "etag": None,
            "error": f"S3 недоступен: {last_exc}",
        }

    return wrapper
