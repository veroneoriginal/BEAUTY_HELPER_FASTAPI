# apps/parser/base.py

# Стратегия сайта: всё, чем один сайт отличается от другого.
# ProductParser (контекст) знает только эти методы и не знает, какой
# сайт ему достался. Перебор прокси и картинка — общие, они в ProductParser.

# Обязательное для каждого сайта:
#   name       — короткое имя сайта, папка картинок: images/<name>/…;
#   hosts      — домены сайта, по ним реестр узнаёт, чья ссылка;
#   fetch_card — сходить на сайт, вернуть сырые данные карточки;
#   extract    — сырые данные → dict с полями ParsedProduct.
# normalize общий: чистка текста, цены и состава от сайта не зависит.
# Сайту нужна особая чистка → переопределяет normalize и зовёт super().
# fetch_card и extract — @abstractmethod: без них наследника не создать.
# name и hosts — атрибуты, их Python не проверяет; проверяет тест реестра.

from abc import ABC, abstractmethod
from typing import Any

from apps.parser.dto import ParsedProduct
from apps.parser.normalizer import normalize
from apps.parser.proxy.models import Proxy


class SiteStrategy(ABC):
    """
    Базовый класс сайта. Объект создать нельзя — только наследника.
    """

    # Имя сайта латиницей, без пробелов и /: "goldapple"
    name: str
    # Домены сайта без www: ("goldapple.ru",)
    hosts: tuple[str, ...] = ()

    @abstractmethod
    async def fetch_card(
        self,
        link: str,
        proxy: Proxy,
    ) -> Any:
        """
        Сырые данные карточки: JSON, HTML — что отдаёт сайт.

        :param link: ссылка на товар
        :param proxy: через какой прокси идём
        :raises SiteBlocked: сайт не пустил — прокси надо менять
        :raises ProductNotFound: товара по ссылке нет
        :raises ParseError: ответ пришёл, но это не карточка
        """

    @abstractmethod
    def extract(
        self,
        card: Any,
        link: str,
    ) -> dict[str, Any]:
        """
        Сырые данные из fetch_card → dict с полями ParsedProduct как есть.

        :param card: то, что вернул fetch_card этой же стратегии
        :param link: ссылка на товар
        :raises ParseError: в данных нет карточки
        """

    def normalize(
        self,
        raw: dict[str, Any],
    ) -> ParsedProduct:
        """
        dict из extract → ParsedProduct. Общий для всех сайтов.

        :param raw: результат extract
        """
        return normalize(raw)
