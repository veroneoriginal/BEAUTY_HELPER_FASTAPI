# Тесты прокси: строка → Proxy, файл со списком, пул.
# Без сети: проверку is_alive в пуле подменяем.

import pytest

from apps.parser.exceptions import NoAliveProxy
from apps.parser.proxy import pool as pool_module
from apps.parser.proxy.models import Proxy, ProxyProtocol
from apps.parser.proxy.pool import ProxyPool
from apps.parser.proxy.source import load_from_file, parse_proxy

HTTP_PROXY = Proxy("85.26.146.169", 80, ProxyProtocol.HTTP)
SOCKS_PROXY = Proxy("195.91.129.101", 1337, ProxyProtocol.SOCKS5)
LOCAL_PROXY = Proxy("127.0.0.1", 10809, ProxyProtocol.HTTP)

# === models ===


def test_proxy_server_string():
    """
    Proxy → строка для Playwright и httpx.
    """
    assert HTTP_PROXY.server == "http://85.26.146.169:80"
    assert str(SOCKS_PROXY) == "socks5://195.91.129.101:1337"


# === source ===


@pytest.mark.parametrize(
    "line, expected",
    [
        ("http://85.26.146.169:80", HTTP_PROXY),
        ("socks5://195.91.129.101:1337", SOCKS_PROXY),
        ("  SOCKS5://195.91.129.101:1337 \n", SOCKS_PROXY),
    ],
)
def test_parse_proxy(line, expected):
    """
    Строка «протокол://ip:порт» → Proxy.
    """
    assert parse_proxy(line) == expected


@pytest.mark.parametrize(
    "line",
    [
        "https://85.26.146.169:80",  # https отдельно не поддерживаем
        "socks4://85.26.146.169:80",
        "http://85.26.146.169",  # нет порта
        "85.26.146.169:80",  # нет протокола
    ],
)
def test_parse_proxy_bad_line(line):
    """
    Кривая строка → ValueError.
    """
    with pytest.raises(ValueError):
        parse_proxy(line)


def test_load_from_file_skips_comments_and_duplicates(tmp_path):
    """
    Комментарии и пустые строки пропускаются, дубли убираются, порядок как в файле.
    """
    path = tmp_path / "proxies.txt"
    path.write_text(
        "# бесплатные RU\n"
        "socks5://195.91.129.101:1337\n"
        "\n"
        "http://85.26.146.169:80\n"
        "socks5://195.91.129.101:1337\n",
        encoding="utf-8",
    )

    assert load_from_file(path) == [SOCKS_PROXY, HTTP_PROXY]


def test_load_from_file_bad_line_has_number(tmp_path):
    """
    Кривая строка → ValueError с именем файла и номером строки.
    """
    path = tmp_path / "proxies.txt"
    path.write_text("http://85.26.146.169:80\nмусор\n", encoding="utf-8")

    with pytest.raises(ValueError, match="proxies.txt, строка 2"):
        load_from_file(path)


# === pool ===


@pytest.fixture
def alive(monkeypatch):
    """
    Подменяет проверку прокси: живые — те, что в наборе.
    Возвращает набор и список проверенных прокси.
    """
    alive_proxies: set[Proxy] = set()
    checked: list[Proxy] = []

    async def fake_is_alive(proxy: Proxy) -> bool:
        checked.append(proxy)
        return proxy in alive_proxies

    monkeypatch.setattr(pool_module, "is_alive", fake_is_alive)
    return alive_proxies, checked


async def test_pool_returns_first_alive(alive):
    """
    Мёртвые по дороге выкидываются, живой отдаётся и остаётся в пуле.
    """
    alive_proxies, checked = alive
    alive_proxies.add(SOCKS_PROXY)
    pool = ProxyPool([HTTP_PROXY, SOCKS_PROXY, LOCAL_PROXY])

    proxy = await pool.get()

    assert proxy == SOCKS_PROXY
    assert checked == [HTTP_PROXY, SOCKS_PROXY]
    # HTTP_PROXY выкинут, SOCKS_PROXY и LOCAL_PROXY остались
    assert len(pool) == 2


async def test_pool_gives_same_alive_proxy_again(alive):
    """
    Живой прокси не выкидывается: следующий get() отдаёт его же.
    """
    alive_proxies, _ = alive
    alive_proxies.add(HTTP_PROXY)
    pool = ProxyPool([HTTP_PROXY, SOCKS_PROXY])

    assert await pool.get() == HTTP_PROXY
    assert await pool.get() == HTTP_PROXY


async def test_pool_all_dead_raises(alive):
    """
    Живых нет → NoAliveProxy, пул пустой.
    """
    pool = ProxyPool([HTTP_PROXY, SOCKS_PROXY])

    with pytest.raises(NoAliveProxy):
        await pool.get()
    assert len(pool) == 0


async def test_empty_pool_raises(alive):
    """
    Пустой список → NoAliveProxy сразу.
    """
    with pytest.raises(NoAliveProxy):
        await ProxyPool([]).get()


async def test_mark_bad_moves_to_next(alive):
    """
    Сайт не пустил → mark_bad, следующий get() даёт другой прокси.
    """
    alive_proxies, _ = alive
    alive_proxies.update({HTTP_PROXY, SOCKS_PROXY})
    pool = ProxyPool([HTTP_PROXY, SOCKS_PROXY])

    pool.mark_bad(await pool.get())

    assert await pool.get() == SOCKS_PROXY


def test_mark_bad_unknown_proxy_is_ignored():
    """
    Прокси нет в пуле → mark_bad ничего не делает.
    """
    pool = ProxyPool([HTTP_PROXY])

    pool.mark_bad(SOCKS_PROXY)

    assert len(pool) == 1


def test_pool_does_not_change_source_list():
    """
    Пул работает с копией: исходный список не портится.
    """
    proxies = [HTTP_PROXY, SOCKS_PROXY]
    pool = ProxyPool(proxies)

    pool.mark_bad(HTTP_PROXY)

    assert proxies == [HTTP_PROXY, SOCKS_PROXY]
