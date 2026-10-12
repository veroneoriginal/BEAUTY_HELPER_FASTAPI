# apps/parser/example_site/strategy.py

# Заглушка второго сайта: показывает, где и что дописать.
# В реестр (registry.py) не добавлена — ссылки на этот сайт
# отклоняются как неподдерживаемые, а не падают посреди парсинга.

# Чтобы подключить настоящий сайт:
#   1. переименовать папку и класс, указать name и домен в hosts;
#   2. реализовать fetch_card (client.py рядом) и extract (extractor.py);
#   3. добавить класс в STRATEGIES в registry.py.

from typing import Any

from apps.parser.base import SiteStrategy
from apps.parser.proxy.models import Proxy


class ExampleSiteStrategy(SiteStrategy):
    """
    Второй сайт — пока заглушка.
    """

    name = "example_site"
    hosts = ("example.com",)

    async def fetch_card(
        self,
        link: str,
        proxy: Proxy,
    ) -> Any:
        """
        Не реализовано: как достать карточку, зависит от сайта.
        """
        raise NotImplementedError("ExampleSiteStrategy.fetch_card — заглушка")

    def extract(
        self,
        card: Any,
        link: str,
    ) -> dict[str, Any]:
        """
        Не реализовано: где лежат поля, зависит от сайта.
        """
        raise NotImplementedError("ExampleSiteStrategy.extract — заглушка")
