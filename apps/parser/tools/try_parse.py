# apps/parser/tools/try_parse.py

# Ручная проверка сборки (шаг 8): ProductParser.parse на живом сайте и настоящем S3.
# Вся цепочка: прокси → карточка → extract → normalize → картинка → ParsedProduct.
#
# Запуск — из корня проекта (команды есть в commands.md):
#   python -m apps.parser.tools.try_parse                   — рабочая ссылка, прокси из пула
#   python -m apps.parser.tools.try_parse --url <ссылка>    — другая, например битая
#   python -m apps.parser.tools.try_parse --proxy http://127.0.0.1:10809
#       — один конкретный прокси вместо пула

import argparse
import asyncio
import time
from dataclasses import fields
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from apps.parser.exceptions import ParserError
from apps.parser.media import ImageUploader
from apps.parser.proxy import pool as pool_module
from apps.parser.proxy.checker import is_alive
from apps.parser.proxy.models import Proxy
from apps.parser.proxy.pool import ProxyPool
from apps.parser.proxy.source import load_from_file, parse_proxy
from apps.parser.service import ProductParser
from core.config import settings
from infrastructure.s3.service import s3_service

DEFAULT_URL = "https://goldapple.ru/19000002015-moisture-surge-100h"

PROXIES_FILE = Path(settings.PARSER_PROXIES_FILE)

# Длинные поля обрезаем, чтобы вывод влез в экран
MAX_VALUE_LENGTH = 100


async def is_alive_verbose(proxy: Proxy) -> bool:
    """
    Та же проверка прокси, что в пуле, только с печатью
    (как в try_client).
    """
    print(f"  проверяю {proxy} на httpbin...", end=" ", flush=True)
    started = time.monotonic()
    alive = await is_alive(proxy)
    print(f"{'живой' if alive else 'мёртвый'} ({time.monotonic() - started:.0f} с)")
    return alive


# Подменяем проверку только для этого скрипта, код пула не меняем
pool_module.is_alive = is_alive_verbose


async def main(url: str, proxy_line: str | None) -> None:
    if proxy_line:
        pool = ProxyPool([parse_proxy(proxy_line)])
    else:
        pool = ProxyPool(load_from_file(PROXIES_FILE))
    print(f"Ссылка: {url}")
    print(f"В пуле: {len(pool)}")
    print(f"Хранилище: {s3_service.endpoint_url}, бакет {s3_service.bucket_name}\n")

    parser = ProductParser(pool, ImageUploader(s3_service))

    started = time.monotonic()
    try:
        product = await parser.parse(url)
    except ParserError as e:
        print(f"\n{type(e).__name__} ({time.monotonic() - started:.0f} с): {e}")
        print(f"В пуле осталось: {len(pool)}")
        return

    print(f"\nOK за {time.monotonic() - started:.0f} с, в пуле осталось: {len(pool)}\n")
    for field in fields(product):
        value = getattr(product, field.name)
        text = repr(value)
        if len(text) > MAX_VALUE_LENGTH:
            text = text[:MAX_VALUE_LENGTH] + "..."
        print(f"  {field.name}: {text}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument(
        "--proxy", help="один прокси вместо пула, например http://127.0.0.1:10809"
    )
    args = parser.parse_args()

    asyncio.run(main(url=args.url, proxy_line=args.proxy))
