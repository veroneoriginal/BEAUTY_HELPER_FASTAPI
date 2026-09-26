# apps/parser/goldapple/normalizer.py

# Normalizer: dict из extractor → ParsedProduct.
# В сеть не ходит. Приводит значения «как на сайте» к нашему формату —
# то, что раньше делалось руками в Excel:
#   HTML → текст, лишние пробелы и \xa0 → один пробел, "" → None,
#   цена и объём → Decimal, состав → список + количество,
#   характеристики → JSON-строка.

import json
import re
from decimal import Decimal, InvalidOperation
from typing import Any

from bs4 import BeautifulSoup

from apps.parser.dto import ParsedProduct

# Поля, в которых сайт присылает HTML
HTML_FIELDS = (
    "description",
    "usage",
    "ingredients",
    "additional_info",
    "brand_description",
)

# Поля с простым текстом
TEXT_FIELDS = (
    "name",
    "article_ga",
    "brand",
    "product_type",
    "product_type_detailed",
    "purpose",
    "hair_type",
    "skin_type",
    "application_area",
    "target_audience",
    "brand_country",
    "measure_type",
    "measure_unit",
    "image_link",
)

# Теги, после которых в тексте начинается новая строка
LINE_BREAK_TAGS = ["br", "p", "li", "div"]

# Разделители состава: «, » и « - » / « – » (Erborian).
# Запятая только с пробелом после неё: иначе «1,2-Hexanediol» развалится на два.
INGREDIENT_SEPARATOR = re.compile(r",\s+|\s+[-–]\s+")


def normalize(raw: dict[str, Any]) -> ParsedProduct:
    """
    Собирает ParsedProduct из dict, который вернул extract().

    :param raw: результат extract(card, link)
    """
    product = ParsedProduct(link_ga=raw["link_ga"])

    for field in TEXT_FIELDS:
        setattr(product, field, clean_text(raw.get(field)))

    for field in HTML_FIELDS:
        setattr(product, field, html_to_text(raw.get(field)))

    product.ingredients_list = split_ingredients(product.ingredients)
    if product.ingredients_list:
        product.ingredients_count = len(product.ingredients_list)

    product.measure_value = to_decimal(raw.get("measure_value"))
    product.price_rub = to_decimal(raw.get("price_rub"))
    product.characteristics = to_json(raw.get("characteristics"))

    return product


def clean_text(value: Any) -> str | None:
    """
    Строка без лишних пробелов: «GIVENCHY  L'INTERDIT» → «GIVENCHY L'INTERDIT».

    split() режет и по \xa0, поэтому неразрывный пробел тоже станет обычным.
    Пустая строка и не строка → None.

    :param value: значение из extractor
    """
    if not isinstance(value, str):
        return None
    text = " ".join(value.split())
    if not text:
        return None
    return text


def html_to_text(value: Any) -> str | None:
    """
    HTML → текст: теги убираем, <p>, <br>, <li> превращаем в переносы строк.

    Пустые строки выкидываем, каждую строку чистим через clean_text.

    :param value: HTML из extractor
    """
    if not isinstance(value, str):
        return None

    soup = BeautifulSoup(value, "html.parser")
    for tag in soup.find_all(LINE_BREAK_TAGS):
        tag.insert_after("\n")

    lines = []
    for line in soup.get_text().splitlines():
        line = clean_text(line)
        if line:
            lines.append(line)

    if not lines:
        return None
    return "\n".join(lines)


def split_ingredients(ingredients: str | None) -> list[str] | None:
    """
    Состав текстом → список элементов.

    Берём только первую строку: дальше бывают пояснения
    («Волокна бамбука: помогают удерживать влагу…»), это не состав.
    С элементов снимаем «*» (сноски) и точку в конце. AQUA/WATER не делим.

    :param ingredients: состав после html_to_text
    """
    if not ingredients:
        return None

    first_line = ingredients.split("\n")[0]

    items = []
    for part in INGREDIENT_SEPARATOR.split(first_line):
        item = part.strip(" *.")
        if item:
            items.append(item)

    if not items:
        return None
    return items


def to_decimal(value: Any) -> Decimal | None:
    """
    Число → Decimal: 13675 → Decimal("13675"), "15" → Decimal("15").

    Через str: Decimal(0.1) от float дал бы 0.1000000000000000055…
    Не число → None.

    :param value: цена или значение меры
    """
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip().replace(",", ".")
    if not text:
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def to_json(value: Any) -> str | None:
    """
    Характеристики (список атрибутов) → JSON-строка, кириллица как есть.

    :param value: список {"key": ..., "value": ...} из extractor
    """
    if not value:
        return None
    return json.dumps(value, ensure_ascii=False)
