# apps/content_generation/openai/json_constructor/main.py

from apps.content_generation.openai.json_constructor.json_creator import (
    JsonCreator,
)
from apps.content_generation.openai.json_constructor.json_processing_data import (
    JsonProcessingData,
)
from apps.products.schemas.structure_for_products import (
    PARAMETERS_DIF_PRODUCT_CATEGORIES,
)
from apps.selection.models import (
    SelectionTaskType,
)


def get_json_scheme(
        task_type: SelectionTaskType,
        data_collection: dict,
) -> dict:
    """
    Функция для получения json-схемы для текущей подборки.

    :param task_type: Тип задачи, по которой создается подборка
    :param data_collection: словарь с информацией по текущей подборке
    такого вида
    {
        'article_ga': '19000002015',
        'image_key': None,
        'ingredients_list': ['Water',
                             'Dimethicone',
                             'Butylene Glycol',
                             'Glycerin',
                             'Trisiloxane',
                             'Trehalose',
                             'Sucrose',
                             ... полный состав],
        'measure_unit': 'мл',
        'measure_value': Decimal('15.00'),
        'name': 'CLINIQUE Moisture Surge 100h',
        'price_rub': Decimal('2100.00'),
        'product_type': 'гель для лица',
        'product_type_detailed': 'Интенсивно увлажняющий гель на 100 часов',
        'Номер шага задачи': 1,
        'Смещение для нумерации': 1,
        'Шаг задачи последний или нет': False,
        'Элементы состава для шага задачи': ['Water',
                                             'Dimethicone',
                                             'Butylene Glycol',
                                             'Glycerin',
                                             'Trisiloxane',
                                             'Trehalose',
                                             ... до 10 элементов],
    }

    :return: json - схема для текущей подборки
    """

    # Создание экземпляра класса обработчика словаря перед созданием json-схемы
    json_processing = JsonProcessingData(
        data_collection=data_collection,
        task_type=task_type,
    )

    # Вызов метода по преобразованию словаря по коду задачи
    new_data_collection = json_processing.distribution_on_task()

    # Создание экземпляра класса по созданию json-схемы
    json_creator = JsonCreator(
        data_collection=new_data_collection,
        product_categories=PARAMETERS_DIF_PRODUCT_CATEGORIES,
    )

    # вызов метода для создания json-схемы
    return json_creator.get_json_scheme_for_current_task()
