# apps/content_generation/openai/json_constructor/json_processing_data.py

from apps.selection.models import (
    SelectionTaskType,
)


class JsonProcessingData:
    """
    Класс, внутри которого преобразовываются данные для текущей подборки
    в зависимости от кода задачи.

    :param data_collection: Словарь с информацией по текущей подборке
    :param task_type: Тип задачи, по которой создается подборка
    """

    def __init__(
            self,
            data_collection: dict,
            task_type: SelectionTaskType,
    ):
        self.data_collection = data_collection
        self.task_type = task_type

        self.method_for_task_code = {
            # код задачи - Подробный анализ каждого элемента состава
            SelectionTaskType.COMPOSITION_ANALYSIS:
                self.conversion_dict_for_task_each_element_composition,
            # "Общий анализ групп элементов состава":
            # self.decryption_task_detailed_analysis_composition,
            # "Аналог": self.decryption_analogue_product,
            # "Лучшее средство": self.decryption_task_best_product,
            # "Лучшее средство без канцерогенов": self.decryption_task_best_product,
            # "Лучшая пара": self.decryption_task_best_couple,
            # "Лучшее сочетание": self.decryption_task_best_combination,
        }

    def distribution_on_task(self):
        """
        С помощью этого метода определяю какую функцию для расшифровки вызывать
        """

        return self.method_for_task_code[self.task_type]()

    def conversion_dict_for_task_each_element_composition(
            self,
    ) -> dict:
        """
        Функция для формирования нового словаря по коду задачи
        SelectionTaskType.COMPOSITION_ANALYSIS или
        "Подробный анализ каждого элемента состава".

        :return: Словарь с необходимыми для json-схемы ключами
        имеет вид
        {
            'article_ga': '19000002015',
            'name': 'CLINIQUE Moisture Surge 100h',
            'product_type': 'гель для лица',
            'product_type_detailed': 'Интенсивно увлажняющий гель на 100 часов',
            'task_type': SelectionTaskType.COMPOSITION_ANALYSIS,
            'Шаг задачи последний или нет': False/True,
            'Элементы состава для шага задачи': ['Water',
                                                 'Dimethicone',
                                                 'Butylene Glycol',
                                                 'Glycerin',
                                                 'Trisiloxane',
                                                 'Trehalose',
                                                 'Sucrose',
                                                 'Ammonium Acryloyldimethyltaurate/vp '
                                                 'Copolymer',
                                                 'Hydroxyethyl Urea',
                                                 'Camellia Sinensis (green Tea) Leaf '
                                                 'Extract'],
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
