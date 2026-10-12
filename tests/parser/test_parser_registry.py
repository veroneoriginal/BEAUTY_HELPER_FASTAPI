# Тесты реестра сайтов и базового класса стратегии: без сети.

import pytest

from apps.parser.base import SiteStrategy
from apps.parser.example_site.strategy import ExampleSiteStrategy
from apps.parser.exceptions import UnsupportedSite
from apps.parser.goldapple.strategy import GoldAppleStrategy
from apps.parser.registry import STRATEGIES, host_from_link, strategy_for


@pytest.mark.parametrize(
    "link",
    [
        "https://goldapple.ru/19000002015-moisture-surge-100h",
        "https://www.goldapple.ru/19000002015-moisture-surge-100h",
        "HTTPS://GoldApple.RU/19000002015",
    ],
)
def test_goldapple_link_gives_goldapple_strategy(link):
    """
    Ссылка ЗЯ с www и без, в любом регистре → GoldAppleStrategy.
    """
    assert isinstance(strategy_for(link), GoldAppleStrategy)


@pytest.mark.parametrize(
    "link",
    [
        "https://example.com/123",  # заглушка не в реестре
        "https://goldapple.ru.evil.com/123",
        "https://notgoldapple.ru/123",
        "goldapple.ru/123",  # без схемы хоста нет
        "abc",
        "",
    ],
)
def test_unknown_link_raises_unsupported_site(link):
    """
    Чужой сайт, похожий домен или не ссылка → UnsupportedSite.
    """
    with pytest.raises(UnsupportedSite):
        strategy_for(link)


def test_host_from_link():
    """
    Хост без www и в нижнем регистре, порт отбрасывается.
    """
    assert host_from_link(" https://WWW.GoldApple.ru:443/x?a=1 ") == "goldapple.ru"


def test_base_strategy_is_abstract():
    """
    SiteStrategy создать нельзя, и наследника без extract — тоже.
    """
    with pytest.raises(TypeError):
        SiteStrategy()

    class NoExtract(SiteStrategy):
        async def fetch_card(self, link, proxy):
            return {}

    with pytest.raises(TypeError):
        NoExtract()


async def test_example_site_is_stub():
    """
    Заглушка создаётся, но методы честно говорят, что не реализованы.
    """
    stub = ExampleSiteStrategy()

    with pytest.raises(NotImplementedError):
        await stub.fetch_card("https://example.com/123", proxy=None)
    with pytest.raises(NotImplementedError):
        stub.extract({}, "https://example.com/123")


@pytest.mark.parametrize(
    "strategy",
    [*STRATEGIES, ExampleSiteStrategy()],
)
def test_strategy_has_name_and_hosts(strategy):
    """
    name и hosts — атрибуты, Python их не проверяет, проверяем тут.
    name идёт в ключ картинки: без пробелов и /.
    """
    assert strategy.name
    assert " " not in strategy.name and "/" not in strategy.name
    assert strategy.hosts


def test_strategy_names_unique():
    """
    Два сайта с одним name сложили бы картинки в одну папку.
    """
    names = [strategy.name for strategy in STRATEGIES]
    assert len(names) == len(set(names))
