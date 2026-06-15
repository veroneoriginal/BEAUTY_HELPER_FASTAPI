# apps/content_generation/openai/prompt_constructor/prompt_constructor.py

from apps.selection.models import (
    SelectionTaskType,
)


class PromptConstructor:
    """
    Класс для построения промптов для отправки в OpenAI.
    Формирует system_prompt и основной prompt на основе расшифрованных данных подборки.
    """

    def __init__(self):
        self.prompts = {
            # Подробный анализ каждого элемента состава
            SelectionTaskType.COMPOSITION_ANALYSIS: self.products_for_detailed_analysis_composition,
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
        task = data_decrypted["task_type"]

        # Определяем функцию для данной задачи
        func_for_work = self.prompts[task]

        return {
            "system_prompt": f"{data_decrypted['specialist']}",
            "prompt": f"""{func_for_work(data_decrypted=data_decrypted)}
    Ответ ты должен дать в следующем виде: {data_decrypted["decryption_task"]}""",
        }

    def products_for_detailed_analysis_composition(
        self,
        data_decrypted: dict,
    ) -> str:
        """
        Формирует текст промпта для задачи COMPOSITION_ANALYSIS.
        Для последнего шага добавляет полный состав для итогового вывода.

        :param data_decrypted: расшифрованные данные подборки
        :return: строка с промптом
        """

        if data_decrypted["Шаг задачи последний или нет"] is True:
            return (
                f"Информация о средстве: {data_decrypted['product_type_detailed']},\n"
                f"название - {data_decrypted['name']}, артикул - {data_decrypted['article_ga']}.\n"
                f"Это финальный шаг — анализировать отдельные компоненты не нужно.\n"
                f"Сделай только общий итоговый вывод по средству, полагаясь на полный состав продукта: \n"
                f"{data_decrypted['ingredients_list']}"
            )

        return (
            f"Информация о средстве: {data_decrypted['product_type_detailed']},\n"
            f"название - {data_decrypted['name']}, артикул - {data_decrypted['article_ga']}.\n"
            f"Информация о части состава этого средства: "
            f"{data_decrypted['Элементы состава для шага задачи']}.\n"
            f"Учти всю вышепредставленную информацию и проведи анализ каждого элемента состава.\n"
            f"Сохраняй нумерацию элементов."
        )

    def main_constructor_prompt(
        self,
        data_decrypted: dict,
    ) -> dict:
        """
        Главный метод класса. Определяет какой промпт отправить в OpenAI.

        :param data_decrypted: расшифрованные данные подборки
        :return: словарь с system_prompt и prompt
        """

        return self.create_prompt_without_user_parameters(
            data_decrypted=data_decrypted,
        )
