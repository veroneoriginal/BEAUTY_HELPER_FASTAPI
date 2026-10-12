# apps/parser/service.py

# Сборка парсера: ссылка → ParsedProduct.
# Сам ничего не разбирает и в сеть не ходит — вызывает готовые куски по очереди:
#   сайт (registry) → прокси (pool) → карточка (strategy.fetch_card)
#   → strategy.extract → strategy.normalize → картинка (media)

# Всё, что зависит от сайта, делает стратегия (base.SiteStrategy).
# Здесь только общее для всех сайтов: перебор прокси и картинка.

# Пул прокси и ImageUploader передаются снаружи: парсер не решает,
# откуда берётся список прокси и в какое хранилище класть картинку.

# Ошибки:
#   UnsupportedSite  — сайта нет в реестре → наверх, в сеть не ходим;
#   SiteBlocked      — сайт не пустил через этот прокси → mark_bad, берём следующий;
#   ProductNotFound  — битая ссылка, другой прокси не поможет → наверх;
#   ParseError       — карточку не разобрать → наверх;
#   NoAliveProxy     — прокси в пуле кончились (бросает pool.get()) → наверх.
# Картинка не загрузилась → image_key = None, парсинг не падает.

import logging
from typing import Any

from apps.parser.base import SiteStrategy
from apps.parser.dto import ParsedProduct
from apps.parser.exceptions import SiteBlocked
from apps.parser.media import ImageUploader
from apps.parser.proxy.models import Proxy
from apps.parser.proxy.pool import ProxyPool
from apps.parser.registry import strategy_for

logger = logging.getLogger(__name__)


class ProductParser:
    """
    Парсер карточки товара: сайт выбирается по ссылке (registry).

    Создаётся один раз вместе с пулом: выкинутые прокси
    не возвращаются от одного парсинга к другому.
    """

    def __init__(
        self,
        pool: ProxyPool,
        uploader: ImageUploader,
    ) -> None:
        """
        :param pool: пул прокси
        :param uploader: загрузка картинки в хранилище
        """
        self.pool = pool
        self.uploader = uploader

    async def parse(
        self,
        link: str,
    ) -> ParsedProduct:
        """
        Ссылка на товар → ParsedProduct со всеми найденными полями и image_key.

        :param link: ссылка на товар
        :raises UnsupportedSite: сайт не поддерживается
        :raises NoAliveProxy: живых прокси не осталось
        :raises ProductNotFound: товара по ссылке нет
        :raises ParseError: карточку не получилось разобрать
        """
        strategy = strategy_for(link)
        card, proxy = await self.fetch_card_via_pool(link, strategy)
        logger.info("[PARSE] Карточка получена через %s, разбираем", proxy)

        raw = strategy.extract(card, link)
        product = strategy.normalize(raw)

        # Картинку качаем через тот же прокси: он только что пустил нас на сайт
        product.image_key = await self.uploader.upload(
            product.image_link,
            product.article,
            strategy.name,
            proxy,
        )
        if product.image_key:
            logger.info("[PARSE] Картинка в хранилище: %s", product.image_key)
        else:
            logger.warning(
                "[PARSE] Картинку загрузить не удалось: %s",
                product.image_link,
            )
        return product

    async def fetch_card_via_pool(
        self,
        link: str,
        strategy: SiteStrategy,
    ) -> tuple[Any, Proxy]:
        """
        Карточка товара и прокси, через который она пришла.

        Сайт не пустил → прокси выкидываем и пробуем следующий.
        Цикл конечный: каждый круг пул становится меньше,
        а пустой пул бросает NoAliveProxy.

        :param link: ссылка на товар
        :param strategy: стратегия сайта из strategy_for
        :raises NoAliveProxy: живых прокси не осталось
        :raises ProductNotFound: товара по ссылке нет
        :raises ParseError: ответ сайта — не карточка
        """
        while True:
            proxy = await self.pool.get()
            logger.info("[PARSE] Загружаем карточку через %s", proxy)
            try:
                card = await strategy.fetch_card(link, proxy)
            except SiteBlocked as exc:
                logger.warning("[PARSE] Сайт не пустил через %s: %s", proxy, exc)
                self.pool.mark_bad(proxy)
                continue
            return card, proxy
