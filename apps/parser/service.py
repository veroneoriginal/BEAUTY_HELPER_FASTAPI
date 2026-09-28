# apps/parser/service.py

# Сборка парсера: ссылка → ParsedProduct.
# Сам ничего не разбирает и в сеть не ходит — вызывает готовые куски по очереди:
#   прокси (pool) → карточка (client) → extract → normalize → картинка (media)

# Пул прокси и ImageUploader передаются снаружи: парсер не решает,
# откуда берётся список прокси и в какое хранилище класть картинку.

# Ошибки:
#   SiteBlocked      — сайт не пустил через этот прокси → mark_bad, берём следующий;
#   ProductNotFound  — битая ссылка, другой прокси не поможет → наверх;
#   ParseError       — карточку не разобрать → наверх;
#   NoAliveProxy     — прокси в пуле кончились (бросает pool.get()) → наверх.
# Картинка не загрузилась → image_key = None, парсинг не падает.

from apps.parser.dto import ParsedProduct
from apps.parser.exceptions import SiteBlocked
from apps.parser.goldapple.client import fetch
from apps.parser.goldapple.extractor import extract
from apps.parser.goldapple.normalizer import normalize
from apps.parser.media import ImageUploader
from apps.parser.proxy.models import Proxy
from apps.parser.proxy.pool import ProxyPool


class ProductParser:
    """
    Парсер карточки товара Золотого Яблока.

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

    async def parse(self, link: str) -> ParsedProduct:
        """
        Ссылка на товар → ParsedProduct со всеми найденными полями и image_key.

        :param link: ссылка на товар в Золотом Яблоке
        :raises NoAliveProxy: живых прокси не осталось
        :raises ProductNotFound: товара по ссылке нет
        :raises ParseError: карточку не получилось разобрать
        """
        card, proxy = await self.fetch_card(link)

        raw = extract(card, link)
        product = normalize(raw)

        # Картинку качаем через тот же прокси: он только что пустил нас на сайт
        product.image_key = await self.uploader.upload(
            product.image_link,
            product.article_ga,
            proxy,
        )
        return product

    async def fetch_card(self, link: str) -> tuple[dict, Proxy]:
        """
        Карточка товара и прокси, через который она пришла.

        Сайт не пустил → прокси выкидываем и пробуем следующий.
        Цикл конечный: каждый круг пул становится меньше,
        а пустой пул бросает NoAliveProxy.

        :param link: ссылка на товар
        :raises NoAliveProxy: живых прокси не осталось
        :raises ProductNotFound: товара по ссылке нет
        :raises ParseError: карточка пришла не в JSON
        """
        while True:
            proxy = await self.pool.get()
            try:
                card = await fetch(link, proxy)
            except SiteBlocked:
                self.pool.mark_bad(proxy)
                continue
            return card, proxy
