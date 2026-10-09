# apps/parser/tools/try_client.py

# Ручная проверка клиента (шаг 3): goldapple.client.fetch на живом сайте.
# Прокси берём из пула (settings.PARSER_PROXIES_FILE). Сайт не пустил (SiteBlocked) →
# mark_bad и следующий прокси — так же будет делать service.py на шаге 8.
#
# Запуск — из корня проекта (команды есть в commands.md):
#   python -m apps.parser.tools.try_client                    — рабочая ссылка
#   python -m apps.parser.tools.try_client --url <ссылка>     — другая, например битая
#   python -m apps.parser.tools.try_client --headed           — с окном браузера
#   python -m apps.parser.tools.try_client --proxy http://127.0.0.1:10809
#       — один конкретный прокси вместо пула: отделить поведение сайта от капризов бесплатных прокси

import argparse
import asyncio
import time
from pathlib import Path

from apps.parser.exceptions import NoAliveProxy, ParserError, SiteBlocked
from apps.parser.goldapple.client import fetch
from apps.parser.proxy import pool as pool_module
from apps.parser.proxy.checker import is_alive
from apps.parser.proxy.models import Proxy
from apps.parser.proxy.pool import ProxyPool
from apps.parser.proxy.source import load_from_file, parse_proxy
from core.config import settings

DEFAULT_URL = "https://goldapple.ru/19000541119-botavikos-blonde"

PROXIES_FILE = Path(settings.PARSER_PROXIES_FILE)


async def is_alive_verbose(proxy: Proxy) -> bool:
    """
    Та же проверка прокси, что в пуле, только с печатью:
    пул проверяет молча, до 10 с на прокси, и кажется, что скрипт завис.
    """
    print(f"  проверяю {proxy} на httpbin...", end=" ", flush=True)
    started = time.monotonic()
    alive = await is_alive(proxy)
    print(f"{'живой' if alive else 'мёртвый'} ({time.monotonic() - started:.0f} с)")
    return alive


# Подменяем проверку только для этого скрипта: пул вызывает is_alive
# через свой модуль, код пула не меняем
pool_module.is_alive = is_alive_verbose


async def main(url: str, headed: bool, proxy_line: str | None) -> None:
    if proxy_line:
        pool = ProxyPool([parse_proxy(proxy_line)])
    else:
        pool = ProxyPool(load_from_file(PROXIES_FILE))
    print(f"Ссылка: {url}")
    print(f"В пуле: {len(pool)}")

    while True:
        print(f"\nИщу живой прокси, в пуле {len(pool)}:")
        try:
            proxy = await pool.get()
        except NoAliveProxy:
            print("Живых прокси не осталось")
            return

        print(f"Иду на ЗЯ через {proxy} (до 60 с)...")
        started = time.monotonic()
        try:
            data = await fetch(url, proxy, headless=not headed)
        except SiteBlocked as e:
            print(f"  SiteBlocked ({time.monotonic() - started:.0f} с): {e}")
            pool.mark_bad(proxy)
            continue
        except ParserError as e:
            # ProductNotFound, ParseError: другой прокси не поможет
            print(f"  {type(e).__name__} ({time.monotonic() - started:.0f} с): {e}")
            return

        product = data.get("data", {})
        print(
            f"  OK ({time.monotonic() - started:.0f} с): {product.get('brand')} {product.get('name')}"
        )
        print(f"  Ключи верхнего уровня: {list(data)}")
        return


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--headed", action="store_true")
    parser.add_argument(
        "--proxy", help="один прокси вместо пула, например http://127.0.0.1:10809"
    )
    args = parser.parse_args()

    asyncio.run(main(url=args.url, headed=args.headed, proxy_line=args.proxy))
