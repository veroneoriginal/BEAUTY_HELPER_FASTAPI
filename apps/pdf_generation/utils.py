# apps/pdf_generation/utils.py
import json
import re
from decimal import Decimal
from types import MappingProxyType

import emoji

from apps.products.services.structure_for_products import (
    MAPPING_KEYS,
)
from core.assets import EMOJI_IMAGE_DIR


def convert_json_openai_to_list(
        analysis_data: str,
) -> list:
    """
    Преобразование Json c ответами от Openai в список словарей

    :param analysis_data: Json со всеми ответами от OPENAI
    :return: список словарей для работы с ответом от OpenAI
    """
    return json.loads(analysis_data)


def convert_analysis_to_pdf_data(
        answer_from_openai: list,
) -> dict:
    """
    Преобразует список словарей c ответами от Openai в словарь с элементами,
    названием средства, выводом, который необходим для генератора PDF.

    :param answer_from_openai: Список словарей с ответом от OpenAI
    :return: словарь с ключами origin_product, result, и всеми элементами состава
    """

    # создаем пустой словарь, который будем наполнять
    result_dict = {}

    # счетчик элементов
    element_counter = 1

    for step in answer_from_openai:
        dict_message = step["answer_openai_to_final"]["message"]

        for key, value in dict_message.items():

            if key.startswith("element_"):
                # Преобразуем к element_1, element_2 и т.д.
                new_key = f"element_{element_counter}"
                result_dict[new_key] = value
                element_counter += 1
            else:
                result_dict[key] = value

    return result_dict


def calculate_price_full_request(
        answer_from_openai: list,
) -> dict:
    """
    Преобразует список словарей c ответами от Openai в словарь,
    в котором содержится только информация по стоимости.

    :param answer_from_openai: Список словарей с ответом от OpenAI
    :return: словарь с ценами запроса
    """

    # создаем заготовку словаря для результата
    assembly_dict = {
        "prompt": {
            "count": 0,
            "USD": Decimal("0.0"),
            "RUB": Decimal("0.0"),
        },
        "completion": {
            "count": 0,
            "USD": Decimal("0.0"),
            "RUB": Decimal("0.0"),
        },
        "total": {
            "count": 0,
            "USD": Decimal("0.0"),
            "RUB": Decimal("0.0"),
        },
    }

    for step in answer_from_openai:
        cost_dict = step["answer_openai_to_final"]["cost_interaction"]

        for part in ("prompt", "completion", "total"):
            part_data = cost_dict.get(part, {})
            assembly_dict[part]["count"] += part_data.get(f"{part}_tokens", 0)
            assembly_dict[part]["USD"] += Decimal(str(part_data.get("USD", 0)))
            assembly_dict[part]["RUB"] += Decimal(str(part_data.get("RUB", 0)))

    return assembly_dict


def translate_keys_to_rus(
        data: dict,
        mapping: MappingProxyType = MAPPING_KEYS,
) -> dict:
    """
    Заменяет ключи во вложенных словарях, опираясь на MAPPING_KEYS.

    :param data: Список словарей с данными.
    :param mapping: Словарь с соответствием новых ключей.
    :return: Новый список словарей с изменёнными/переведенными ключами.
    """
    if isinstance(data, dict):
        return {
            mapping.get(key, key): translate_keys_to_rus(value, mapping)
            for key, value in data.items()
        }
    return data


def calculate_price_per_standard_unit(
        quantity: str,
        unit: str,
        price_rub: int | float,
) -> str:
    """
    Рассчитывает стоимость за стандартный объем (100 или 50) в зависимости
    от количества и единицы измерения.

    :param quantity: Количество меры (например, 250, 50, 2)
    :param unit: Юниты меры (например, "мл", "гр", "л")
    :param price_rub: Стоимость в рублях

    :return: Строку с информацией о стоимости за стандартное
    количество (100 или 50) с учётом единицы измерения.
    """
    quantity = int(quantity)

    # Конвертация в базовые единицы
    conversion_factors = {
        "л": ("мл", 1000),  # 1 л = 1000 мл
        "кг": ("гр", 1000),  # 1 кг = 1000 гр
        "мл": ("мл", 1),
        "гр": ("гр", 1),
        "г": ("г", 1),
    }

    if unit in conversion_factors:
        base_unit, factor = conversion_factors[unit]
        base_quantity = quantity * factor
    else:
        raise ValueError(f"Неизвестная единица измерения: {unit}")

    # Выбор стандартного количества:
    if base_quantity <= 50:
        standard_quantity = 10
    elif base_quantity < 100:
        standard_quantity = 50
    else:
        standard_quantity = 100

    # Рассчитываем цену за стандартное количество
    price_per_standard = (price_rub / base_quantity) * standard_quantity
    return f'{standard_quantity} {base_unit} / {int(price_per_standard)} р.'


def extract_product_name(
        title: str,
) -> str:
    """
    Удаляет из строки (артикул: 123456)
    """
    return re.sub(r"\s*\(артикул:.*?\)", "", title, flags=re.IGNORECASE).strip()


def calc_base_price_ratio(
        product: dict,
) -> str:
    """
    Готовит строку 'Количество мера / цена'
    Например: '190 мл / 1612 р.'

    :param product: словарь с информацией по одному средству
    :return: str
    """

    return (
        f'{product.get("measure_value")} '
        f'{product.get("measure_unit")} / {product.get("price_rub")} руб'
    )


def capitalize_first_letter(
        text: str,
) -> str:
    """
    Делает первую букву заглавной
    """
    for i, char in enumerate(text):
        if char.isalpha():
            return text[:i] + char.upper() + text[i + 1:]
    return text  # если букв вообще нет


def unicode_to_twemoji_codepoint(
        char: str,
) -> str:
    """
    Преобразует emoji в codepoint-строку, исключая FE0F, если надо
    """

    codepoints = [f"{ord(c):x}" for c in char]

    # Если последний элемент FE0F — пробуем без него
    if codepoints[-1] == 'fe0f':
        test_path = EMOJI_IMAGE_DIR / f"{'-'.join(codepoints[:-1])}.png"
        if test_path.exists():
            codepoints = codepoints[:-1]

    return '-'.join(codepoints)


def replace_emoji_html(
        text: str,
        size=16,
) -> str:
    """
    Заменяет emoji символы на <img> с реальным путем, понятным ReportLab.
    """
    new_text = ''
    last_index = 0

    for e in emoji.emoji_list(text):
        start = e['match_start']
        end = e['match_end']
        emoji_char = text[start:end]
        codepoint = unicode_to_twemoji_codepoint(emoji_char)

        # Путь для ReportLab должен быть читаемым на диске
        img_path = EMOJI_IMAGE_DIR / f"{codepoint}.png"
        img_path_str = img_path.resolve().as_posix()  # абсолютный Unix-путь

        # Генерация тега
        img_tag = f'<img src="{img_path_str}" width="{size}" height="{size}"/>'

        new_text += text[last_index:start] + img_tag
        last_index = end

    new_text += text[last_index:]

    return new_text
