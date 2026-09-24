# apps/parser/proxy/checker.py

# Проверка прокси: живой ли он и пропускает ли HTTPS.
# Проверяем не на Золотом Яблоке, а на нейтральном адресе httpbin.org/ip:
# он отвечает IP, с которого пришёл запрос, — видно, что адрес подменился.
# Адрес https://, потому что ЗЯ тоже https: прокси, который не умеет
# пропускать HTTPS-трафик, проверку не пройдёт.

# Проверяем через httpx, а не через Playwright: поднимать браузер ради
# «отвечает ли прокси» слишком тяжело. SOCKS5 в httpx — через httpx[socks].

import httpx
from socksio.exceptions import ProtocolError as SocksProtocolError

from apps.parser.proxy.models import Proxy

CHECK_URL = "https://httpbin.org/ip"

# Сколько ждём ответа от одного прокси, секунд.
# Бесплатные прокси медленные, но дольше 10 с — всё равно непригоден.
DEFAULT_TIMEOUT = 10.0


async def is_alive(
    proxy: Proxy,
    timeout: float = DEFAULT_TIMEOUT,
) -> bool:
    """
    Один прокси: True, если через него пришёл нормальный ответ.

    :param proxy: какой прокси проверяем
    :param timeout: сколько ждать ответа, секунд
    """
    try:
        async with httpx.AsyncClient(proxy=proxy.server, timeout=timeout) as client:
            response = await client.get(CHECK_URL)
            response.raise_for_status()
            # httpbin отвечает {"origin": "<ip>"}; нет поля — отвечал не httpbin
            return "origin" in response.json()
    except httpx.HTTPError:
        # не подключился, таймаут, плохой статус
        return False
    except SocksProtocolError:
        # SOCKS5-прокси ответил не по протоколу (сломан или это не SOCKS5).
        # httpx не заворачивает эту ошибку в свою, ловим отдельно
        return False
    except ValueError:
        # в ответе не JSON: прокси подсунул свою страницу
        return False
