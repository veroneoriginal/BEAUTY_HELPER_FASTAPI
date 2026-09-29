# Тесты normalizer: dict из extractor → ParsedProduct.
# Отдельные функции чистки — на строках, весь normalize — на сохранённых карточках.

import json
from decimal import Decimal

import pytest

from apps.parser.dto import ParsedProduct
from apps.parser.goldapple.extractor import extract
from apps.parser.goldapple.normalizer import (
    clean_text,
    html_to_text,
    normalize,
    split_ingredients,
    to_decimal,
    to_json,
)

# === clean_text ===


@pytest.mark.parametrize(
    "value, expected",
    [
        ("GIVENCHY  L'INTERDIT", "GIVENCHY L'INTERDIT"),
        ("  крем\xa0для лица \n", "крем для лица"),
        ("", None),
        ("   ", None),
        (None, None),
        (123, None),
    ],
)
def test_clean_text(value, expected):
    """
    Лишние пробелы и \\xa0 → один пробел; пусто и не строка → None.
    """
    assert clean_text(value) == expected


# === html_to_text ===


def test_html_paragraphs_become_lines():
    """
    <p> и <br> → переносы строк, теги убраны.
    """
    html = "<p>первый абзац</p><p>второй<br>третий</p>"

    assert html_to_text(html) == "первый абзац\nвторой\nтретий"


def test_html_strong_does_not_break_line():
    """
    <strong> внутри строки не рвёт её (ради этого не get_text("\\n")).
    """
    html = "<p><strong>страна</strong> Япония</p>"

    assert html_to_text(html) == "страна Япония"


def test_html_list_items():
    """
    Каждый <li> — своя строка.
    """
    html = "<ul><li>раз</li><li>два</li></ul>"

    assert html_to_text(html) == "раз\nдва"


@pytest.mark.parametrize("value", ["", "<p></p>", "<p>  </p>", None])
def test_html_empty_is_none(value):
    """
    Пустой HTML → None.
    """
    assert html_to_text(value) is None


# === split_ingredients ===


def test_split_by_comma():
    """
    Запятая с пробелом — разделитель.
    """
    assert split_ingredients("Aqua, Glycerin, Dimethicone") == [
        "Aqua",
        "Glycerin",
        "Dimethicone",
    ]


def test_split_keeps_comma_without_space():
    """
    1,2-Hexanediol не разваливается: запятая без пробела — часть названия.
    """
    assert split_ingredients("Aqua, 1,2-Hexanediol, Glycerin") == [
        "Aqua",
        "1,2-Hexanediol",
        "Glycerin",
    ]


@pytest.mark.parametrize("dash", ["-", "–"])
def test_split_by_dash(dash):
    """
    « - » и « – » — разделители (Erborian), дефис внутри слова — нет.
    """
    text = f"AQUA/WATER {dash} GLYCERIN {dash} PEG-10 DIMETHICONE"

    assert split_ingredients(text) == ["AQUA/WATER", "GLYCERIN", "PEG-10 DIMETHICONE"]


def test_split_strips_asterisk_and_dot():
    """
    Сноски * и точка в конце снимаются.
    """
    assert split_ingredients("Aqua*, Glycerin**, Parfum.") == [
        "Aqua",
        "Glycerin",
        "Parfum",
    ]


def test_split_takes_only_first_line():
    """
    После первой строки — пояснения, это не состав.
    """
    text = "Aqua, Glycerin\nВолокна бамбука: помогают удерживать влагу"

    assert split_ingredients(text) == ["Aqua", "Glycerin"]


@pytest.mark.parametrize("value", [None, "", " * . "])
def test_split_empty_is_none(value):
    """
    Нет состава → None, а не пустой список.
    """
    assert split_ingredients(value) is None


# === to_decimal ===


@pytest.mark.parametrize(
    "value, expected",
    [
        (13675, Decimal("13675")),
        ("15", Decimal("15")),
        ("2,5", Decimal("2.5")),
        (99.5, Decimal("99.5")),
        (None, None),
        ("", None),
        ("abc", None),
        (True, None),
    ],
)
def test_to_decimal(value, expected):
    """
    Числа и строки с числом → Decimal; не число → None.
    """
    assert to_decimal(value) == expected


# === to_json ===


def test_to_json_makes_dict_with_cyrillic():
    """
    Список атрибутов → JSON-строка словаря, кириллица без \\u-кодов.
    """
    attributes = [
        {"key": "тип продукта", "value": "крем для лица"},
        {"key": "объём", "value": "50 мл"},
    ]

    result = to_json(attributes)

    assert json.loads(result) == {"тип продукта": "крем для лица", "объём": "50 мл"}
    assert "крем" in result


@pytest.mark.parametrize("value", [None, []])
def test_to_json_empty_is_none(value):
    """
    Нет характеристик → None.
    """
    assert to_json(value) is None


# === normalize на сохранённых карточках ===


def test_normalize_all_fixtures(article, load_card, make_link):
    """
    Каждая карточка → ParsedProduct с правильными типами.
    """
    raw = extract(load_card(article), make_link(article))

    product = normalize(raw)

    assert isinstance(product, ParsedProduct)
    assert product.article_ga == article
    assert isinstance(product.price_rub, Decimal)
    assert isinstance(product.measure_value, Decimal)
    assert isinstance(json.loads(product.characteristics), dict)
    # image_key ставит ImageUploader, не normalizer
    assert product.image_key is None
    # Состав и его количество всегда согласованы
    if product.ingredients_list is None:
        assert product.ingredients_count is None
    else:
        assert product.ingredients_count == len(product.ingredients_list)
    # В текстовых полях не осталось HTML
    for text in (product.description, product.ingredients, product.usage):
        assert text is None or "<" not in text


def test_normalize_clinique(load_card, make_link):
    """
    Clinique Moisture Surge: итог сверен с сайтом (живой запуск 29.09).
    """
    raw = extract(load_card("19000002015"), make_link("19000002015"))

    product = normalize(raw)

    assert product.name == "CLINIQUE Moisture Surge 100h"
    assert product.brand == "Clinique"
    assert product.product_type == "крем-гель для лица"
    assert product.measure_type == "объём"
    assert product.measure_value == Decimal("15")
    assert product.measure_unit == "мл"
    assert product.price_rub == Decimal("2200")
    assert product.hair_type is None
    assert product.ingredients_count == 42
    assert product.ingredients_list[0] == "Water/Aqua/Eau"
    # Служебный хвост оставляем как на сайте
    assert product.ingredients_list[-1] == "Yellow 5 (CI 19140) [ILN50944]"


def test_normalize_erborian_ingredients(load_card, make_link):
    """
    Erborian: состав через « - », пояснения после него не попадают в список.
    """
    raw = extract(load_card("9400200001"), make_link("9400200001"))

    product = normalize(raw)

    assert product.ingredients_count == 31
    assert product.ingredients_list[0] == "AQUA/WATER"
    assert "1,2-HEXANEDIOL" in product.ingredients_list
    # Пояснения идут следующими строками — в полном тексте они есть
    assert "\n" in product.ingredients


def test_normalize_without_ingredients(load_card, make_link):
    """
    Givenchy без раздела «Состав» → весь состав None.
    """
    raw = extract(load_card("3680300002"), make_link("3680300002"))

    product = normalize(raw)

    assert product.ingredients is None
    assert product.ingredients_list is None
    assert product.ingredients_count is None


def test_normalize_empty_brand_description(load_card, make_link):
    """
    Brand.content = "" у Frudia → None.
    """
    raw = extract(load_card("9410400008"), make_link("9410400008"))

    product = normalize(raw)

    assert product.brand_description is None
