# apps/content_generation/openai/prompt_constructor/main.py

from apps.content_generation.openai.prompt_constructor.prompt_constructor import (
    PromptConstructor,
)
from apps.content_generation.openai.prompt_constructor.prompt_processing_data import (
    PromptProcessingData,
)
from apps.selection.models import (
    SelectionTaskType,
)


def get_prompts(
        task_type: SelectionTaskType,
        data_collection: dict,
) -> dict:
    """
    Функция для создания промпта.

    :param task_type: Тип задачи, по которой создается подборка
    :param data_collection: Словарь с текущим шагом подборки

    :return: Промпт в виде словаря вида:
    {
    'prompt': 'Информация о средстве: Интенсивно увлажняющий гель на 100 часов,\n'
               'название - CLINIQUE Moisture Surge 100h, артикул - 19000002015.\n'
               'Информация о части состава этого средства: 1_Water, 2_Dimethicone, '
               '3_Butylene Glycol, 4_Glycerin, 5_Trisiloxane, 6_Trehalose, '
               '7_Sucrose, 8_Ammonium Acryloyldimethyltaurate/vp Copolymer, '
               '9_Hydroxyethyl Urea, 10_Camellia Sinensis (green Tea) Leaf '
               'Extract.\n'
               'Учти всю вышепредставленную информацию и проведи анализ каждого '
               'элемента состава.\n'
               'Сохраняй нумерацию элементов.\n'
               '    Ответ ты должен дать в следующем виде: Тебе дано средство и '
               'часть элементов его состава. Тебе надо разобрать каждый элемент '
               'состава средства. Внимательно изучаешь и выдаёшь результат в '
               'соответствии с json схемой. Ответы должны быть понятны человеку '
               'без медицинского образования, старайся отвечать понятно, без '
               'сложных формулировок. Отвечай всегда на русском языке.',
    'system_prompt': 'Ты высококвалифицированный врач. Твоя задача подобрать '
                      'максимально подходящее средство для человека. Данные '
                      'человека будут даны.',
    }
    """

    # 1 расшифровываем данные из текущей подборки
    prompt_proces_data = PromptProcessingData(
        data_collection=data_collection,
        task_type=task_type,
    )
    result_decrypted_data = prompt_proces_data.decryption_data_current_collection()

    # 2 формируем промпт на основе расшифрованных данных
    prompt_constructor = PromptConstructor()

    return prompt_constructor.main_constructor_prompt(
        data_decrypted=result_decrypted_data,
    )
