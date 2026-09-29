# Тесты ProductParser.parse: сборка всей цепочки без сети.
# fetch подменяем (карточка — из fixtures/), проверку прокси — тоже,
# ImageUploader — свой класс, который только запоминает вызов.

import pytest

from apps.parser import service as service_module
from apps.parser.exceptions import (
    NoAliveProxy,
    ParseError,
    ProductNotFound,
    SiteBlocked,
)
from apps.parser.proxy import pool as pool_module
from apps.parser.proxy.models import Proxy, ProxyProtocol
from apps.parser.proxy.pool import ProxyPool
from apps.parser.service import ProductParser

ARTICLE = "19000002015"
LINK = f"https://goldapple.ru/{ARTICLE}-moisture-surge-100h"

FIRST = Proxy("85.26.146.169", 80, ProxyProtocol.HTTP)
SECOND = Proxy("195.91.129.101", 1337, ProxyProtocol.SOCKS5)


class FakeUploader:
    """
    Вместо ImageUploader: запоминает, что пришло, и отдаёт ключ.
    """

    def __init__(self, image_key: str | None = f"images/{ARTICLE}.jpg") -> None:
        self.image_key = image_key
        self.calls: list[tuple] = []

    async def upload(self, image_link, article, proxy=None):
        self.calls.append((image_link, article, proxy))
        return self.image_key


@pytest.fixture(autouse=True)
def all_proxies_alive(monkeypatch):
    """
    Все прокси проходят проверку httpbin — сеть не трогаем.
    """

    async def fake_is_alive(proxy: Proxy) -> bool:
        return True

    monkeypatch.setattr(pool_module, "is_alive", fake_is_alive)


@pytest.fixture
def site(monkeypatch, load_card):
    """
    Подменяет client.fetch. Ответы сайта задаются по прокси:
    site[proxy] = исключение → fetch его бросает; нет в словаре — отдаёт карточку.
    Возвращает словарь ответов и список прокси, через которые ходили.
    """
    errors: dict[Proxy, Exception] = {}
    used: list[Proxy] = []

    async def fake_fetch(link: str, proxy: Proxy) -> dict:
        used.append(proxy)
        if proxy in errors:
            raise errors[proxy]
        return load_card(ARTICLE)

    monkeypatch.setattr(service_module, "fetch", fake_fetch)
    return errors, used


async def test_parse_full_chain(site):
    """
    Карточка → ParsedProduct, картинка качается через тот же прокси.
    """
    _, used = site
    uploader = FakeUploader()
    parser = ProductParser(ProxyPool([FIRST, SECOND]), uploader)

    product = await parser.parse(LINK)

    assert product.link_ga == LINK
    assert product.article_ga == ARTICLE
    assert product.name == "CLINIQUE Moisture Surge 100h"
    assert product.image_key == f"images/{ARTICLE}.jpg"
    assert used == [FIRST]
    assert uploader.calls == [(product.image_link, ARTICLE, FIRST)]


async def test_site_blocked_takes_next_proxy(site):
    """
    SiteBlocked → прокси выкидывается, карточку берём через следующий.
    Картинку качаем через тот прокси, который пустил.
    """
    errors, used = site
    errors[FIRST] = SiteBlocked("403")
    uploader = FakeUploader()
    pool = ProxyPool([FIRST, SECOND])

    product = await ProductParser(pool, uploader).parse(LINK)

    assert product.article_ga == ARTICLE
    assert used == [FIRST, SECOND]
    assert len(pool) == 1
    assert uploader.calls[0][2] == SECOND


async def test_all_blocked_raises_no_alive_proxy(site):
    """
    Сайт не пустил ни через один прокси → NoAliveProxy, пул пустой.
    """
    errors, _ = site
    errors[FIRST] = SiteBlocked("403")
    errors[SECOND] = SiteBlocked("таймаут")
    pool = ProxyPool([FIRST, SECOND])

    with pytest.raises(NoAliveProxy):
        await ProductParser(pool, FakeUploader()).parse(LINK)
    assert len(pool) == 0


@pytest.mark.parametrize(
    "error",
    [ProductNotFound("страница не найдена"), ParseError("не JSON")],
)
async def test_other_errors_go_up_without_retry(site, error):
    """
    ProductNotFound и ParseError — другой прокси не поможет:
    ошибка наверх, прокси остаётся в пуле, картинку не качаем.
    """
    errors, used = site
    errors[FIRST] = error
    pool = ProxyPool([FIRST, SECOND])
    uploader = FakeUploader()

    with pytest.raises(type(error)):
        await ProductParser(pool, uploader).parse(LINK)
    assert used == [FIRST]
    assert len(pool) == 2
    assert uploader.calls == []


async def test_image_failed_parse_still_works(site):
    """
    Картинка не загрузилась → image_key = None, товар всё равно возвращается.
    """
    parser = ProductParser(ProxyPool([FIRST]), FakeUploader(image_key=None))

    product = await parser.parse(LINK)

    assert product.name == "CLINIQUE Moisture Surge 100h"
    assert product.image_key is None
