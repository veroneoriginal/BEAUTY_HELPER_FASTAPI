# apps/content_generation/openai/prompt_constructor/prompt_processing_data.py

from apps.content_generation.openai.prompt_constructor.data_task import (
    SPECIALISTS,
    full_data_task,
)
from apps.content_generation.openai.prompt_constructor.utils import (
    format_composition_elements,
    get_specialist_by_product_type,
)
from apps.selection.models import (
    SelectionTaskType,
)


class PromptProcessingData:
    """
    Класс для расшифровки данных текущей подборки в зависимости от типа задачи.
    Преобразует сырые данные продукта в структуру необходимую для построения промпта.

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
            SelectionTaskType.COMPOSITION_ANALYSIS:
                self.decrypting_info_code_detailed_analysis_composition,
        }

    def decryption_data_current_collection(
            self,
    ) -> dict:
        """
        Выбирает и вызывает метод расшифровки в зависимости от типа задачи.

        :return: Словарь с расшифрованными данными по текущей подборке вида
        {
        'article_ga': '19000002015',
        'decryption_task': 'Тебе дано средство и часть элементов его состава. Тебе '
                            'надо разобрать каждый элемент состава средства. '
                            'Внимательно изучаешь и выдаёшь результат в соответствии с '
                            'json схемой. Ответы должны быть понятны человеку без '
                            'медицинского образования, старайся отвечать понятно, без '
                            'сложных формулировок. Отвечай всегда на русском языке.',

        'name': 'CLINIQUE Moisture Surge 100h',
        'product_type_detailed': 'Интенсивно увлажняющий гель на 100 часов',
        'specialist': 'Ты высококвалифицированный врач. Твоя задача подобрать '
                        'максимально подходящее средство для человека. Данные человека '
                        'будут даны.',
        'task_type': SelectionTaskType.COMPOSITION_ANALYSIS,
        'Номер шага задачи': 1,
        'Шаг задачи последний или нет': False,
        'Элементы состава для шага задачи': '1_Water, 2_Dimethicone, 3_Butylene '
                                            'Glycol, 4_Glycerin, 5_Trisiloxane, '
                                            '6_Trehalose, 7_Sucrose, 8_Ammonium '
                                            'Acryloyldimethyltaurate/vp Copolymer, '
                                            '9_Hydroxyethyl Urea, 10_Camellia '
                                            'Sinensis (green Tea) Leaf Extract',
        'ingredients_list' : [],
        }
        """

        return self.method_for_task_code[self.task_type]()

    def decrypting_info_code_detailed_analysis_composition(
            self,
    ) -> dict:
        """
        Расшифровывает данные для задачи SelectionTaskType.COMPOSITION_ANALYSIS
        (Подробный анализ каждого элемента состава).

        :return dict: Возвращает словарь с данными,
        которые необходимы для формирования промпта
        """
        # формируем новый словарь
        decrypting_data_collection = {}

        # 1. Определяем специалиста по типу продукта
        product_type = self.data_collection['product_type']
        specialist = get_specialist_by_product_type(product_type)

        if specialist is not None:
            # 2 расшифровываем специалиста и добавляем этот ключ в новый словарь
            decrypting_data_collection['specialist'] = SPECIALISTS[specialist]
        else:
            decrypting_data_collection['specialist'] = SPECIALISTS["DEFAULT"]

        # 3 Получаем элементы состава
        composition_elements = self.data_collection['Элементы состава для шага задачи']

        # Пронумеровываем их и конвертируем список в строку
        start_index = self.data_collection.get('Смещение для нумерации', 1)
        formatted_string = format_composition_elements(
            elements=composition_elements,
            start_index=start_index,
        )

        #  добавляем ключ в новый словарь
        decrypting_data_collection['Элементы состава для шага задачи'] = formatted_string

        # 4 Добавляем ключ с именем продукта в новый словарь
        decrypting_data_collection['name'] = self.data_collection['name']

        # 5 добавляем ключ с артикулом товара в новый словарь
        decrypting_data_collection['article_ga'] = self.data_collection['article_ga']

        # 6 добавляем исходную задачу в новый словарь
        decrypting_data_collection['task_type'] = self.task_type

        # 7 добавляем в новый словарь дополнительные ключи, которые не нужно расшифровывать
        decrypting_data_collection['Номер шага задачи'] = self.data_collection['Номер шага задачи']
        decrypting_data_collection['Шаг задачи последний или нет'] = self.data_collection[
            'Шаг задачи последний или нет']

        # 8 добавляем в новый словарь детализацию продукта
        decrypting_data_collection['product_type_detailed'] = self.data_collection[
            'product_type_detailed']

        # 9 расшифровываем задачу и добавляем ее в новый словарь, если необходимо дополняем
        base_instruction = full_data_task[self.task_type]

        if self.data_collection['Шаг задачи последний или нет'] is True:
            base_instruction += (
                "\n\nТакже добавь итоговый `result` — общий вывод по данному средству в целом, "
                "основываясь на полный состав продукта, который дан выше. "
                "Описывать все компоненты состава не нужно, только сделай краткий вывод "
                "о качестве этого состава в целом, кому может подойти/не подойти средство и т.д."
            )

        decrypting_data_collection['decryption_task'] = base_instruction

        # 10 добавляем полный список элементов состава
        decrypting_data_collection['ingredients_list'] = self.data_collection['ingredients_list']

        print("Функция decrypting_info_code_detailed_analysis_composition")
        print(decrypting_data_collection)

        return decrypting_data_collection
