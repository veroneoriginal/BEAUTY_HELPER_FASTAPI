# apps/parser/proxy/source.py

# Откуда пул берёт прокси.
# Сейчас — из текстового файла, по одному адресу на строку:
#     http://85.26.146.169:80
#     socks5://195.91.129.101:1337
# Строки с # и пустые пропускаются.
# Второй источник — сайт freeproxyupdate.com: HTML-таблица со списком.
# Он тоже отдаёт list[Proxy], остальной пул от источника не зависит.

from pathlib import Path
from urllib.parse import urlsplit

import httpx
from bs4 import BeautifulSoup

from apps.parser.proxy.models import Proxy, ProxyProtocol

SITE_URL = "https://freeproxyupdate.com/russia-ru"
SITE_TIMEOUT = 30  # секунд на ответ сайта

# Протокол в таблице сайта → схема адреса.
# https на сайте — это HTTP-прокси с поддержкой HTTPS (см. ProxyProtocol).
# socks4 и прочее пул не умеет — такие строки пропускаем.
SITE_PROTOCOLS = {
    "http": "http",
    "https": "http",
    "socks5": "socks5",
}


def parse_proxy(line: str) -> Proxy:
    """
    Одна строка «протокол://ip:порт» → Proxy.

    :param line: строка из списка, например "socks5://195.91.129.101:1337"
    :raises ValueError: строка не похожа на адрес прокси
    """
    parts = urlsplit(line.strip())
    # ValueError, если протокол не http / socks5
    protocol = ProxyProtocol(parts.scheme.lower())

    if not parts.hostname or not parts.port:
        raise ValueError(f"Нет ip или порта: {line!r}")

    return Proxy(host=parts.hostname, port=parts.port, protocol=protocol)


def load_from_file(path: Path) -> list[Proxy]:
    """
    Читает список прокси из файла.

    Дубли убираются, порядок сохраняется — как в файле.
    Кривая строка роняет загрузку с номером строки:
    файл пишем руками, ошибку лучше увидеть сразу.

    :param path: путь к файлу со списком
    """
    proxies: dict[Proxy, None] = {}  # dict, а не set: set не хранит порядок

    lines = path.read_text(encoding="utf-8").splitlines()
    for number, line in enumerate(lines, start=1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            proxies[parse_proxy(line)] = None
        except ValueError as error:
            raise ValueError(f"{path.name}, строка {number}: {error}") from error

    return list(proxies)


def parse_site_html(html: str) -> list[Proxy]:
    """
    Разбирает таблицу прокси со страницы freeproxyupdate.com.

    Столбцы: ip, порт, страна, протокол, ... Кривые строки и
    неподдерживаемые протоколы пропускаются: список чужой, и одна
    плохая строка не должна ронять весь разбор.
    Дубли убираются, порядок — как на сайте.

    :param html: HTML страницы со списком
    """
    proxies: dict[Proxy, None] = {}

    soup = BeautifulSoup(html, "html.parser")
    for row in soup.select("table.list-proxy tbody tr"):
        cells = [cell.get_text(strip=True) for cell in row.find_all("td")]
        if len(cells) < 4:
            continue

        host, port, _country, protocol = cells[:4]
        scheme = SITE_PROTOCOLS.get(protocol.lower())
        if scheme is None:
            continue

        try:
            proxies[parse_proxy(f"{scheme}://{host}:{port}")] = None
        except ValueError:
            continue

    return list(proxies)


def load_from_site(url: str = SITE_URL, timeout: float = SITE_TIMEOUT) -> list[Proxy]:
    """
    Скачивает страницу со списком прокси и разбирает её.

    :param url: адрес страницы со списком
    :param timeout: сколько ждать ответа, секунд
    :raises httpx.HTTPError: сайт не ответил или ответил ошибкой
    """
    response = httpx.get(
        url,
        timeout=timeout,
        follow_redirects=True,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    response.raise_for_status()

    return parse_site_html(response.text)
