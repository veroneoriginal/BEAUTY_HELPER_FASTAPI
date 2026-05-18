# apps/content_generation/openai/task_processing/utils.py

def formation_context(
        dict_with_prompts: dict,
) -> list:
    """
    Функция для формирования контекста - то есть распределения
    промпта и системного промпта по правильной схеме, необходимой
    для отправки запроса в OPENAI.

    :param dict_with_prompts: Словарь с системным и обычным промптом
    для отправки запроса

    :return: подготовленный список для отправки запроса
    """

    return [
        {
            'role': 'system',
            'content': [
                {
                    'type': 'text',
                    'text': dict_with_prompts['system_prompt'],
                }
            ]
        },

        {
            'role': 'user',
            'content': [
                {
                    'type': 'text',
                    'text': dict_with_prompts['prompt'],
                }
            ]
        }
    ]


def create_request_details(
        json_scheme: dict,
        context: list,
) -> dict:
    """
    Функция для формирования полного словаря с информацией о запросе
    :param json_scheme: json-схема текущего запроса
    :param context: контекст текущего запроса

    :return: словарь с информацией о запросе для его передачи в OPENAI
    """
    return {
        'service': 'openai',
        'model': 'gpt-4o-mini',
        'target': 'text',
        'json_scheme': json_scheme,
        'context': context,
    }
