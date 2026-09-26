# apps/parser/proxy/pool.py

# Пул прокси: выдаёт живой прокси, через который клиент идёт в сеть.

# Как работает get():
#   берём первый прокси из списка → проверяем (checker)
#   → живой: отдаём его, он остаётся в пуле
#   → мёртвый: выкидываем из пула и берём следующий
#   → список кончился: NoAliveProxy

# Если прокси прошёл проверку, но сайт через него не пустил (403, обрыв),
# сервис (service.py) зовёт mark_bad(proxy) — прокси выкидывается, следующий get() даст другой.

# Выкидываем только из пула в памяти, файл со списком не трогаем:
# бесплатный прокси, мёртвый сейчас, через час может ожить.

from apps.parser.exceptions import NoAliveProxy
from apps.parser.proxy.checker import is_alive
from apps.parser.proxy.models import Proxy


class ProxyPool:
    """
    Пул прокси.

    Живёт, пока живёт процесс: создали один раз из списка
    и дальше только берём прокси через get().
    """

    def __init__(self, proxies: list[Proxy]) -> None:
        """
        :param proxies: кандидаты, например из source.load_from_file
        """
        # Копия: пул выкидывает мёртвые, исходный список не портим
        self._proxies = list(proxies)

    def __len__(self) -> int:
        """
        Сколько прокси ещё осталось в пуле.
        """
        return len(self._proxies)

    async def get(self) -> Proxy:
        """
        Первый живой прокси.

        Мёртвые по дороге выкидываются из пула.

        :raises NoAliveProxy: живых не осталось
        """
        while self._proxies:
            proxy = self._proxies[0]

            if await is_alive(proxy):
                return proxy

            self.mark_bad(proxy)

        raise NoAliveProxy("В пуле не осталось живых прокси")

    def mark_bad(self, proxy: Proxy) -> None:
        """
        Выкинуть прокси из пула.

        Зовёт сам пул (прокси не прошёл проверку)
        и сервис (сайт не пустил через этот прокси).

        :param proxy: какой прокси выкидываем
        """
        if proxy in self._proxies:
            self._proxies.remove(proxy)
