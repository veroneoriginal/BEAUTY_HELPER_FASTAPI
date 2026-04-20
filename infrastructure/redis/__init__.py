# infrastructure/redis/__init__.py

# Асинхронный клиент Redis.
# Используется для blacklist токенов при logout.

import redis.asyncio as redis

from core.config import settings

# Пул соединений — переиспользуется всем приложением
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD,
    decode_responses=True,
)
