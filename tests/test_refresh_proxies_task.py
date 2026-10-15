# Тесты Celery-задачи refresh_proxies_task без сети и Redis.
# load_from_site и redis_client подменены: проверяем, когда задача
# пишет список в Redis, а когда оставляет старый.

import json
from unittest.mock import MagicMock, patch

import httpx

from apps.parser.proxy.models import Proxy, ProxyProtocol
from apps.parser.proxy.store import PROXIES_KEY, load_proxies, save_proxies
from infrastructure.celery import tasks

HTTP_PROXY = Proxy("85.26.146.169", 80, ProxyProtocol.HTTP)
SOCKS_PROXY = Proxy("195.91.129.101", 1337, ProxyProtocol.SOCKS5)


def _run(load_from_site) -> MagicMock:
    """
    Запускает задачу с подменённым сайтом и Redis, возвращает мок Redis.
    """
    redis_client = MagicMock()
    with (
        patch.object(tasks, "load_from_site", load_from_site),
        patch.object(tasks, "redis_client", redis_client),
    ):
        tasks.refresh_proxies_task()
    return redis_client


def test_saves_fresh_list():
    """
    Сайт отдал прокси — список и время обновления лежат в Redis.
    """
    redis_client = _run(MagicMock(return_value=[HTTP_PROXY, SOCKS_PROXY]))

    redis_client.set.assert_called_once()
    key, value = redis_client.set.call_args.args
    data = json.loads(value)
    assert key == PROXIES_KEY
    assert data["proxies"] == [
        "http://85.26.146.169:80",
        "socks5://195.91.129.101:1337",
    ]
    assert data["updated_at"]


def test_site_error_keeps_old_list():
    """
    Сайт не ответил — в Redis ничего не пишем, задача не падает.
    """
    redis_client = _run(MagicMock(side_effect=httpx.ConnectTimeout("timeout")))

    redis_client.set.assert_not_called()


def test_empty_list_keeps_old_list():
    """
    Сайт отдал пустую таблицу — старый список не затираем.
    """
    redis_client = _run(MagicMock(return_value=[]))

    redis_client.set.assert_not_called()


def test_store_roundtrip_and_missing_key():
    """
    save_proxies → load_proxies отдаёт тот же список; ключа нет — None.
    """
    data = {}
    redis_client = MagicMock()
    redis_client.set.side_effect = lambda key, value: data.__setitem__(key, value)
    redis_client.get.side_effect = data.get

    assert load_proxies(redis_client) is None

    updated_at = save_proxies(redis_client, [HTTP_PROXY, SOCKS_PROXY])
    assert load_proxies(redis_client) == (updated_at, [HTTP_PROXY, SOCKS_PROXY])
