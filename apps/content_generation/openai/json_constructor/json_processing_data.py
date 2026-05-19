# apps/content_generation/openai/json_constructor/json_processing_data.py

from apps.selection.models import SelectionTaskType


class JsonProcessingData:
    """
    Класс для подготовки данных перед созданием JSON-схемы.
    Формирует словарь с нужными полями в зависимости от типа задачи.

    :param data_collection: словарь с данными текущего шага подборки
    :param task_type: тип задачи подборки
    """

    def __init__(
            self,
            data_collection: dict,
            task_type: SelectionTaskType,
    ):
        self.data_collection = data_collection
        self.task_type = task_type

        self.method_for_task_code = {
            # Подробный анализ каждого элемента состава
            SelectionTaskType.COMPOSITION_ANALYSIS:
                self.conversion_dict_for_task_each_element_composition,
            # "Общий анализ элементов состава": self.decryption_task_detailed_analysis_composition,
            # "Аналог": self.decryption_analogue_product,
        }

    def distribution_on_task(self):
        """
        Определяет и вызывает метод подготовки данных в зависимости от типа задачи.

        :return: подготовленный словарь для создания JSON-схемы
        """

        return self.method_for_task_code[self.task_type]()

    def conversion_dict_for_task_each_element_composition(
            self,
    ) -> dict:
        """
        Формирует словарь для задачи COMPOSITION_ANALYSIS /
        Подробный анализ каждого элемента состава.

        :return:
        {
            'article_ga': '19000002015',
            'name': 'CLINIQUE Moisture Surge 100h',
            'product_type': 'гель для лица',
            'product_type_detailed': 'Интенсивно увлажняющий гель на 100 часов',
            'task_type': SelectionTaskType.COMPOSITION_ANALYSIS,
            'Шаг задачи последний или нет': False/True,
            'Элементы состава для шага задачи': ['Water', 'Dimethicone', ..., 'Extract'],
        }
        """

        # Создаем новый словарь
        data = {}

        # Сохраняем в новом словаре информацию о запросе
        data["task_type"] = self.task_type

        # Наполняем новый словарь нужными данными
        data["name"] = self.data_collection["name"]
        data["product_type"] = self.data_collection["product_type"]
        data["product_type_detailed"] = self.data_collection["product_type_detailed"]
        data["article_ga"] = self.data_collection["article_ga"]
        data['Элементы состава для шага задачи'] = self.data_collection[
            'Элементы состава для шага задачи']
        data["Шаг задачи последний или нет"] = self.data_collection["Шаг задачи последний или нет"]

        return data
