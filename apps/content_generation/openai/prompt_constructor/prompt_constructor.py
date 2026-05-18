# apps/content_generation/openai/prompt_constructor/prompt_constructor.py

from apps.selection.models import (
    SelectionTaskType,
)


class PromptConstructor:
    """
    Класс для создания промптов для отправки в контекст OPENAI
    """

    def __init__(self):
        self.prompts = {
            # 'Подробный анализ каждого элемента состава'
            SelectionTaskType.COMPOSITION_ANALYSIS:
                self.products_for_detailed_analysis_composition,
        }

    def create_prompt_without_user_parameters(
            self,
            data_decrypted: dict,
    ) -> dict:
        """
        Метод для формирования текстового промпта для отправки в OPENAI БЕЗ учёта
        параметров пользователя

        :param data_decrypted: словарь с данными по текущей подборке
        :return: словарь с системным промптом и основным промптом за отправки запроса.
        """

        # Получаем код задачи
        task = data_decrypted['task_type']

        # Определяем функцию для данной задачи
        func_for_work = self.prompts[task]

        return {
            'system_prompt': f"{data_decrypted['specialist']}",
            'prompt': f"""{func_for_work(data_decrypted=data_decrypted)}
    Ответ ты должен дать в следующем виде: {data_decrypted["decryption_task"]}"""
        }

    def products_for_detailed_analysis_composition(
            self,
            data_decrypted: dict,
    ) -> str:
        """
        Метод для формирования текстового описания блока со средствами
        для кода 'Подробный анализ каждого элемента состава'.

        :param data_decrypted: Словарь с данными по текущей подборке
        :return: строка с описанием средств
        """

        if data_decrypted['Шаг задачи последний или нет'] is True:
            return f"""Информация о средстве: {data_decrypted['product_type_detailed']},
название - {data_decrypted['name']}, артикул - {data_decrypted['article_ga']}.
Информация о части состава этого средства: {data_decrypted['Элементы состава для шага задачи']}.
Учти всю вышепредставленную информацию и проведи анализ каждого элемента состава.
Сохраняй нумерацию элементов.
Сделай вывод по всему средству, полагаясь на полный состав продукта: 
{data_decrypted['ingredients_list']}"""

        return f"""Информация о средстве: {data_decrypted['product_type_detailed']},
название - {data_decrypted['name']}, артикул - {data_decrypted['article_ga']}.
Информация о части состава этого средства: {data_decrypted['Элементы состава для шага задачи']}.
Учти всю вышепредставленную информацию и проведи анализ каждого элемента состава.
Сохраняй нумерацию элементов."""

    def main_constructor_prompt(
            self,
            data_decrypted: dict,
    ) -> dict:
        """
        Главная функция класса, которая определяет какой промпт будет отправлен в OpenAI.

        :param data_decrypted: Словарь с данными по текущей подборке
        :return: словарь с промптом
        """

        return self.create_prompt_without_user_parameters(
            data_decrypted=data_decrypted,
        )
