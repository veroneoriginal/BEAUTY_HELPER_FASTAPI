# apps/parser/proxy/store.py

# Свежий список прокси с сайта лежит в Redis одним ключом:
#     {"updated_at": "2026-10-15T14:00:00+00:00",
#      "proxies": ["http://62.182.159.194:3128", ...]}
# Пишет его Celery-задача refresh_proxies_task раз в час.
# updated_at нужен воркеру парсинга: список новее его пула — пул пересоздаём.

import json
from datetime import datetime, timezone

from redis import Redis

from apps.parser.proxy.models import Proxy
from apps.parser.proxy.source import parse_proxy

PROXIES_KEY = "parser:proxies"


def save_proxies(redis_client: Redis, proxies: list[Proxy]) -> datetime:
    """
    Записывает список прокси в Redis вместе с временем обновления.

    Ключ без TTL: если сайт надолго ляжет, остаётся последний список.

    :param redis_client: клиент Redis
    :param proxies: список прокси, уже разобранный и без дублей
    :return: время обновления, которое записали
    """
    updated_at = datetime.now(timezone.utc)
    redis_client.set(
        PROXIES_KEY,
        json.dumps(
            {
                "updated_at": updated_at.isoformat(),
                "proxies": [proxy.server for proxy in proxies],
            }
        ),
    )
    return updated_at


def load_proxies(redis_client: Redis) -> tuple[datetime, list[Proxy]] | None:
    """
    Читает список прокси из Redis.

    Строки в ключе пишет save_proxies, поэтому кривых быть не должно;
    если всё же попалась — пропускаем, как и при разборе сайта.

    :param redis_client: клиент Redis
    :return: (время обновления, список) или None, если ключа нет
    """
    raw = redis_client.get(PROXIES_KEY)
    if raw is None:
        return None

    data = json.loads(raw)
    proxies = []
    for line in data["proxies"]:
        try:
            proxies.append(parse_proxy(line))
        except ValueError:
            continue

    return datetime.fromisoformat(data["updated_at"]), proxies
