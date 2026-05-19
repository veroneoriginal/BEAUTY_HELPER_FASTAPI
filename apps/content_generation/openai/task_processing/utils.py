# apps/content_generation/openai/task_processing/utils.py

def formation_context(
        dict_with_prompts: dict,
) -> list:
    """
    Формирует контекст для отправки запроса в OpenAI.
    Распределяет system_prompt и prompt по правильной структуре.

    :param dict_with_prompts: словарь с ключами system_prompt и prompt
    :return: список словарей в формате OpenAI API
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
    Формирует финальный словарь с информацией о запросе для передачи в OpenAI.

    :param json_scheme: JSON-схема текущего запроса
    :param context: контекст текущего запроса
    :return: словарь с параметрами запроса
    """
    return {
        'service': 'openai',
        'model': 'gpt-4o-mini',
        'target': 'text',
        'json_scheme': json_scheme,
        'context': context,
    }
