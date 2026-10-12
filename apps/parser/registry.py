# apps/parser/registry.py

# Реестр сайтов: по ссылке выбирает стратегию.
# Новый сайт = новый класс-наследник SiteStrategy + строка в STRATEGIES,
# ProductParser и остальной код не трогаем.

# Хост сравниваем без www и регистра: www.GoldApple.ru → goldapple.ru.

from urllib.parse import urlsplit

from apps.parser.base import SiteStrategy
from apps.parser.exceptions import UnsupportedSite
from apps.parser.goldapple.strategy import GoldAppleStrategy

# Подключённые сайты. ExampleSiteStrategy — заглушка, сюда не добавлена
STRATEGIES: tuple[SiteStrategy, ...] = (GoldAppleStrategy(),)


def host_from_link(link: str) -> str:
    """
    Хост ссылки без www: «https://www.goldapple.ru/123» → «goldapple.ru».

    :param link: ссылка на товар
    """
    host = (urlsplit(link.strip()).hostname or "").lower()
    return host.removeprefix("www.")


def strategy_for(link: str) -> SiteStrategy:
    """
    Стратегия сайта, которому принадлежит ссылка.

    :param link: ссылка на товар
    :raises UnsupportedSite: сайта нет в STRATEGIES
    """
    host = host_from_link(link)
    for strategy in STRATEGIES:
        if host in strategy.hosts:
            return strategy
    raise UnsupportedSite(f"Сайт не поддерживается: {link}")
