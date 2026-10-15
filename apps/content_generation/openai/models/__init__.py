# apps/content_generation/openai/models/__init__.py
# Настройки по моделям: новая модель — новый файл рядом и строка в MODELS

from types import ModuleType

from apps.content_generation.openai.models import gpt_4o_mini

MODELS = {
    "gpt-4o-mini": gpt_4o_mini,
}


def get_model_settings(model: str) -> ModuleType:
    """
    Возвращает модуль с настройками модели по её названию из OPENAI_MODEL.

    :param model: название модели, например "gpt-4o-mini"
    :return: модуль с ценами, лимитами и параметрами запроса
    :raises ValueError: если для модели нет файла с настройками
    """

    if model not in MODELS:
        raise ValueError(
            f"Нет настроек для модели OpenAI '{model}'. Добавьте файл в "
            f"apps/content_generation/openai/models/ и строку в MODELS. "
            f"Доступные модели: {', '.join(MODELS)}"
        )

    return MODELS[model]
