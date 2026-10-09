# apps/parser/tools/check_proxies.py

# Ручная проверка пула: загружаем список прокси (settings.PARSER_PROXIES_FILE) в ProxyPool
# и просим один живой прокси — так же, как это будет делать парсер.
#
# Запуск — из корня проекта (команда есть в commands.md):
#   python -m apps.parser.tools.check_proxies

import asyncio
from pathlib import Path

from apps.parser.exceptions import NoAliveProxy
from apps.parser.proxy.pool import ProxyPool
from apps.parser.proxy.source import load_from_file
from core.config import settings

PROXIES_FILE = Path(settings.PARSER_PROXIES_FILE)


async def main() -> None:
    pool = ProxyPool(load_from_file(PROXIES_FILE))
    print(f"В пуле: {len(pool)}. Ищу живой...")

    try:
        proxy = await pool.get()
    except NoAliveProxy:
        print("Живых нет, пул пуст")
        return

    print(f"Живой: {proxy}")
    print(f"Осталось в пуле: {len(pool)}")


if __name__ == "__main__":
    asyncio.run(main())
