# apps/parser/proxy/models.py

# Прокси как объект: адрес, порт, протокол.
# Остальные части пула (source, checker, pool) работают только с ним.
# Playwright принимает прокси строкой: {"server": "http://ip:port"},
# поэтому здесь же — перевод объекта в эту строку.

import enum
from dataclasses import dataclass


class ProxyProtocol(str, enum.Enum):
    """
    Протокол прокси — схема в адресе (http://, socks5://).

    HTTPS отдельно не выделяем: в списках так помечают HTTP-прокси,
    который умеет пропускать HTTPS-трафик. Для Playwright это тот же http://.
    """

    HTTP = "http"
    SOCKS5 = "socks5"


@dataclass(slots=True, frozen=True)
class Proxy:
    """
    Один прокси-сервер.

    frozen=True — объект неизменяемый и хешируемый:
    его можно класть в set, так из списка убираются дубли.
    """

    host: str  # IP-адрес
    port: int  # Порт
    protocol: ProxyProtocol  # Протокол

    @property
    def server(self) -> str:
        """
        Адрес для Playwright: {"server": proxy.server}.
        """
        return f"{self.protocol.value}://{self.host}:{self.port}"

    def __str__(self) -> str:
        """
        Короткая запись для логов — тот же адрес: socks5://195.91.129.101:1337.
        """
        return self.server
