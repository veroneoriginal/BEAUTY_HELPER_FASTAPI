# apps/parser/goldapple/extractor.py

# Extractor: сырой JSON карточки → dict с полями ParsedProduct.
# В сеть не ходит, только достаёт значения из JSON как есть:
# HTML, пустые строки, цена числом — всё это чистит normalizer

# Где что лежит — таблица в for_claude/research.md.
# Разделы описания ищем по type / text, а не по индексу:
# порядок разделов на сайте может поменяться.
# Нет поля → None, это не ошибка.

from typing import Any
from urllib.parse import urlsplit

from apps.parser.exceptions import ParseError

# Атрибуты раздела «Описание»: ключ на сайте → поле ParsedProduct
ATTRIBUTE_FIELDS = {
    "тип продукта": "product_type",
    "назначение": "purpose",
    "тип волос": "hair_type",
    "тип кожи": "skin_type",
    "область применения": "application_area",
    "для кого": "target_audience",
}

# Текстовые разделы: заголовок на сайте → поле ParsedProduct
TEXT_SECTION_FIELDS = {
    "Применение": "usage",
    "Состав": "ingredients",
    "Информация и документы": "additional_info",
}

# Картинка приходит шаблоном: .../<хеш>${screen}.${format}
IMAGE_SCREEN = "fullhd"
IMAGE_FORMAT = "jpg"


def extract(
    card: dict,
    link: str,
) -> dict[str, Any]:
    """
    Достаёт поля товара из JSON карточки.

    :param card: JSON из client.fetch — {"data": {...}}
    :param link: ссылка на товар, из неё берём артикул
    :raises ParseError: в JSON нет data — это не карточка
    """
    data = card.get("data")
    if not isinstance(data, dict):
        raise ParseError(f"В ответе нет data: {link}")

    article = article_from_link(link) or data.get("id")
    variant = _find_variant(data, article)
    sections = data.get("productDescription") or []
    description = _find_section(sections, section_type="Description")
    brand = _find_section(sections, section_type="Brand")

    result: dict[str, Any] = {
        "link_ga": link,
        "article_ga": article,
        "name": description.get("title"),
        "brand": data.get("brand"),
        "product_type_detailed": data.get("productType"),
        "description": description.get("content"),
        "brand_country": brand.get("subtitle"),
        "brand_description": brand.get("content"),
        # Все атрибуты «Описания» как есть; в JSON-строку превращает normalizer
        "characteristics": description.get("attributes"),
    }

    # Атрибуты «Описания»: тип продукта, назначение, тип кожи и т.д.
    for field in ATTRIBUTE_FIELDS.values():
        result[field] = None
    for attribute in description.get("attributes") or []:
        field = ATTRIBUTE_FIELDS.get(attribute.get("key"))
        if field:
            result[field] = attribute.get("value")

    # Текстовые разделы: применение, состав, информация
    for text, field in TEXT_SECTION_FIELDS.items():
        result[field] = _find_section(sections, text=text).get("content")

    result.update(_extract_measure(data, variant))
    result["price_rub"] = _extract_price(variant)
    result["image_link"] = _extract_image(variant)

    return result


def article_from_link(link: str) -> str | None:
    """
    Артикул из ссылки: .../19000002015-moisture-surge-100h → 19000002015.

    :param link: ссылка на товар
    """
    # path = "/19000002015-moisture-surge-100h"
    path = urlsplit(link).path.strip("/")
    article = path.split("-")[0]
    if article.isdigit():
        return article
    return None


def _find_variant(
    data: dict,
    article: str | None,
) -> dict:
    """
    Вариант товара из ссылки.

    У товара бывает несколько вариантов (объёмы, оттенки) со своими
    артикулами, ценой и картинкой. Берём тот, чей артикул в ссылке,
    не нашли — первый.

    :param data: data из JSON карточки
    :param article: артикул из ссылки
    """
    variants = data.get("variants") or []
    for variant in variants:
        if variant.get("itemId") == article:
            return variant
    if variants:
        return variants[0]
    return {}


def _find_section(
    sections: list[dict],
    section_type: str | None = None,
    text: str | None = None,
) -> dict:
    """
    Раздел описания по type («Description», «Brand») или по заголовку («Состав»).

    Не нашли — пустой dict: дальше .get() вернёт None.

    :param sections: data.productDescription
    :param section_type: тип раздела
    :param text: заголовок раздела
    """
    for section in sections:
        if section_type and section.get("type") == section_type:
            return section
        if text and section.get("text") == text:
            return section
    return {}


def _extract_measure(
    data: dict,
    variant: dict,
) -> dict[str, Any]:
    """
    Мера: вид («объём»), значение («200»), единица («мл»).

    Вид и единица общие для товара (data.attributes.units),
    значение — у варианта (attributesValue.units): у объёмов 50 и 100 мл
    разные варианты.

    :param data: data из JSON карточки
    :param variant: выбранный вариант
    """
    units = (data.get("attributes") or {}).get("units") or {}
    values = variant.get("attributesValue") or {}
    return {
        "measure_type": units.get("label"),
        "measure_value": values.get("units"),
        "measure_unit": units.get("unit"),
    }


def _extract_price(variant: dict) -> int | None:
    """
    Цена со скидкой: price.actual.amount.
    В Decimal переводит normalizer.

    :param variant: выбранный вариант
    """
    price = variant.get("price") or {}
    actual = price.get("actual") or {}
    return actual.get("amount")


def _extract_image(variant: dict) -> str | None:
    """
    Ссылка на первую картинку с подставленным размером и форматом.

    :param variant: выбранный вариант
    """
    images = variant.get("imageUrls") or []
    if not images:
        return None
    url = images[0].get("url")
    if not url:
        return None
    return url.replace("${screen}", IMAGE_SCREEN).replace("${format}", IMAGE_FORMAT)
