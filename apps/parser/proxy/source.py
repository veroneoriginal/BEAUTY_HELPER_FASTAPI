# apps/parser/proxy/source.py

# Откуда пул берёт прокси.
# Сейчас — из текстового файла, по одному адресу на строку:
#     http://85.26.146.169:80
#     socks5://195.91.129.101:1337
# Строки с # и пустые пропускаются.
# Потом рядом появится загрузка с сайта (freeproxyupdate.com):
# она тоже должна отдавать list[Proxy], остальной пул не поменяется.

from pathlib import Path
from urllib.parse import urlsplit

from apps.parser.proxy.models import Proxy, ProxyProtocol


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
