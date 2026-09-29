# Тесты extractor: JSON карточки → dict «как на сайте».
# Без сети, на сохранённых карточках из fixtures/.

import pytest

from apps.parser.exceptions import ParseError
from apps.parser.goldapple.extractor import article_from_link, extract

# Givenchy L'Interdit: 5 вариантов в одном JSON, у каждого свой объём и цена
GIVENCHY = "3680300002"


@pytest.mark.parametrize(
    "link, expected",
    [
        ("https://goldapple.ru/19000002015-moisture-surge-100h", "19000002015"),
        ("https://goldapple.ru/19000002015-moisture-surge-100h/", "19000002015"),
        ("https://goldapple.ru/19000002015-moisture-surge-100h?utm=tg", "19000002015"),
        ("https://goldapple.ru/l-interdit", None),
        ("https://goldapple.ru/", None),
    ],
)
def test_article_from_link(link, expected):
    """
    Артикул — число в начале пути; нет числа → None.
    """
    assert article_from_link(link) == expected


def test_extract_all_fixtures(article, load_card, make_link):
    """
    Каждая карточка разбирается: ссылка, артикул, название, цена и картинка на месте.
    """
    link = make_link(article)

    raw = extract(load_card(article), link)

    assert raw["link_ga"] == link
    assert raw["article_ga"] == article
    assert raw["name"]
    assert raw["brand"]
    assert raw["price_rub"] is not None
    assert raw["image_link"].startswith("https://")
    # Шаблон ${screen}.${format} подставлен
    assert "${" not in raw["image_link"]


def test_extract_keeps_values_as_is(load_card, make_link):
    """
    Extractor ничего не чистит: HTML остаётся, цена числом, объём строкой.
    """
    raw = extract(load_card("9400200001"), make_link("9400200001"))

    assert raw["ingredients"].startswith("<p>")
    assert raw["price_rub"] == 3570
    assert raw["measure_value"] == "50"
    assert raw["measure_type"] == "объём"
    assert raw["measure_unit"] == "мл"
    # Характеристики — список атрибутов, в JSON-строку превращает normalizer
    assert isinstance(raw["characteristics"], list)


@pytest.mark.parametrize(
    "article, volume, price",
    [
        ("3680300002", "50", 13675),
        ("19000019660", "125", 21555),
        ("19000359496", "100", 18910),
        ("3680300001", "35", 9760),
        ("3680300003", "80", 16775),
    ],
)
def test_variant_by_article_from_link(article, volume, price, load_card):
    """
    Вариант выбирается по артикулу из ссылки: у каждого объёма своя цена.
    """
    link = f"https://goldapple.ru/{article}-l-interdit"

    raw = extract(load_card(GIVENCHY), link)

    assert raw["article_ga"] == article
    assert raw["measure_value"] == volume
    assert raw["price_rub"] == price
    assert f"/{article}/" in raw["image_link"]


def test_no_article_in_link_takes_data_id(load_card):
    """
    В ссылке нет артикула → берём data.id и его вариант.
    """
    raw = extract(load_card(GIVENCHY), "https://goldapple.ru/l-interdit")

    assert raw["article_ga"] == GIVENCHY
    assert raw["measure_value"] == "50"


def test_unknown_article_takes_first_variant(load_card):
    """
    Артикула из ссылки нет среди вариантов → первый вариант,
    и артикул тоже его, а не из ссылки.
    """
    raw = extract(load_card(GIVENCHY), "https://goldapple.ru/3680399999-l-interdit")

    assert raw["article_ga"] == GIVENCHY
    assert raw["measure_value"] == "50"
    assert raw["price_rub"] == 13675
    assert f"/{GIVENCHY}/" in raw["image_link"]


def test_missing_sections_are_none(load_card, make_link):
    """
    У Givenchy нет разделов «Состав» и «Применение» → None, а не ошибка.
    """
    raw = extract(load_card(GIVENCHY), make_link(GIVENCHY))

    assert raw["ingredients"] is None
    assert raw["usage"] is None
    assert raw["hair_type"] is None


def test_out_of_stock_still_has_price(load_card, make_link):
    """
    Товар не в наличии (19000074476): цена в JSON всё равно есть.
    """
    raw = extract(load_card("19000074476"), make_link("19000074476"))

    assert raw["price_rub"] == 3204


@pytest.mark.parametrize("card", [{}, {"data": None}, {"data": []}])
def test_no_data_raises_parse_error(card):
    """
    В ответе нет data → это не карточка, ParseError.
    """
    with pytest.raises(ParseError):
        extract(card, "https://goldapple.ru/19000002015-test")


def test_empty_data_gives_none_fields():
    """
    data пустая → все поля None, кроме ссылки и артикула из неё.
    """
    raw = extract({"data": {}}, "https://goldapple.ru/19000002015-test")

    assert raw["article_ga"] == "19000002015"
    assert raw["name"] is None
    assert raw["price_rub"] is None
    assert raw["image_link"] is None
    assert raw["measure_value"] is None
