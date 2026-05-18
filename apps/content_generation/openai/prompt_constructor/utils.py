# apps/content_generation/openai/prompt_constructor/utils.py

from apps.content_generation.openai.prompt_constructor.data_task import (
    PRODUCT_CATEGORIES_FOR_SPECIALISTS,
)


def get_specialist_by_product_type(
        product_type: str,
) -> str | None:
    """
    Определяет категорию специалиста по типу продукта.

    :param product_type: Тип продукта (например, "шампунь").
    :return str: Название категории специалиста (например, "Трихолог"),
    либо None, если не найдено соответствие.
    """
    for specialist, product_types in PRODUCT_CATEGORIES_FOR_SPECIALISTS.items():
        if product_type in product_types:
            return specialist
    return None


def format_composition_elements(
        elements: list[str],
        start_index: int = 1,
) -> str:
    """
    Форматирует список элементов состава в строку
    с порядковыми номерами, начиная с указанного индекса.

    :param elements: Список элементов состава.
    :param start_index: Начальный номер для нумерации элементов.
    :return: Строка вида "1_Element, 2_Element, ..."
    """
    result = []
    current_index = start_index
    for element in elements:
        result.append(f"{current_index}_{element}")
        current_index += 1
    return ', '.join(result)
