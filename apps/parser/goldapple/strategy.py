# apps/parser/goldapple/strategy.py

# Стратегия Золотого Яблока: тонкая обёртка над client.fetch
# и extractor.extract, сама ничего не разбирает.
# Как устроен сайт — в комментариях client.py и extractor.py.

from typing import Any

from apps.parser.base import SiteStrategy
from apps.parser.goldapple.client import fetch
from apps.parser.goldapple.extractor import extract
from apps.parser.proxy.models import Proxy


class GoldAppleStrategy(SiteStrategy):
    """
    Золотое Яблоко: карточка — JSON из API, достаём через Playwright.
    """

    name = "goldapple"
    hosts = ("goldapple.ru",)

    async def fetch_card(
        self,
        link: str,
        proxy: Proxy,
    ) -> dict:
        """
        JSON карточки из API product-card/base/v3.

        :param link: ссылка на товар
        :param proxy: через какой прокси идём
        """
        return await fetch(link, proxy)

    def extract(
        self,
        card: dict,
        link: str,
    ) -> dict[str, Any]:
        """
        JSON карточки → dict с полями ParsedProduct.

        :param card: JSON из fetch_card
        :param link: ссылка на товар
        """
        return extract(card, link)
