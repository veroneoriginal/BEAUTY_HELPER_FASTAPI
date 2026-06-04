# apps/content_generation/openai/tokenizer/main.py
import json
from typing import Dict, List

import tiktoken

from apps.content_generation.openai.settings import (
    ADD_INDENTATION,
    ADD_TOKENS_FOR_STOCK,
    HEADER_TOKENS_COUNT,
)

# В этом модуле осуществляется подсчет токенов
# ключевая функция main_count_tokens, из нее идет вызов всех остальных


def checking_type_data_context(
    context: list,
) -> list:
    """
    Проверяет тип данных контекста перед подсчётом токенов.

    :param context: контекст для отправки в OpenAI
    :return: тот же список, если всё ок
    :raises TypeError: если context не список или содержит не словари
    """

    if not isinstance(context, list):
        raise TypeError(
            f"Аргумент {context} должен быть списком, а не {type(context).__name__}."
        )

    if not all(isinstance(item, dict) for item in context):
        raise TypeError("Все элементы списка должны быть словарями.")

    return context


def checking_type_data_json_scheme(
    json_scheme: dict,
) -> dict:
    """
    Проверяет что json_scheme является словарём.

    :param json_scheme: json-схема для отправки в OpenAI
    :return: тот же словарь, если всё ок
    :raises TypeError: если json_scheme не словарь
    """

    if not isinstance(json_scheme, dict):
        raise TypeError(
            f"Аргумент json_scheme должен быть словарём, "
            f"а не {type(json_scheme).__name__}."
        )

    return json_scheme


def checking_relevance_model_name(
    model: str,
) -> tiktoken.Encoding:
    """
    Подбирает энкодер tiktoken для указанной модели GPT.

    :param model: название модели OpenAI
    :return: объект tiktoken.Encoding для указанной модели
    :raises ValueError: если модель не поддерживается tiktoken
    """

    try:
        encoding = tiktoken.encoding_for_model(model)
        return encoding

    except KeyError as exc:
        raise ValueError(f"Модель '{model}' не поддерживается.") from exc


def prepares_text_for_counting(
    context: list,
) -> str:
    """
    Преобразует контекст в строку для подсчёта токенов.

    :param context: контекст для отправки в OpenAI
    :return: все текстовые сообщения объединённые в одну строку
    """

    # Инициализируем переменную для объединения всех текстовых сообщений
    full_text_list = []

    # Проходим по каждому словарю в списке content
    for message in context:
        # Проверяем, есть ли ключ 'content' в словаре
        if "content" in message:
            full_text_list.append(message["content"])

    result_list = []

    for item in full_text_list:
        for elements_dict in item:
            result_list.append(elements_dict["text"])

    return " ".join(result_list)


def prepares_json_for_counting(
    json_scheme: dict,
) -> str:
    """
    Преобразует json_scheme в строку для подсчёта токенов.

    :param json_scheme: json-схема для отправки в OpenAI
    :return: json_scheme в виде строки
    """

    return json.dumps(json_scheme, ensure_ascii=False)


def count_tokens(
    entity_count: str,
    encoding: tiktoken.Encoding,
) -> int:
    """
    Подсчитывает количество токенов в строке.

    :param entity_count: строка для подсчёта
    :param encoding: энкодер tiktoken для конкретной модели
    :return: количество токенов
    """

    return len(encoding.encode(entity_count))


def main_count_tokens(
    context: List[Dict[str, str]],
    model: str,
    json_scheme: dict | None,
) -> int:
    """
    Главная функция модуля. Считает итоговое количество токенов
    в контексте и json-схеме с учётом служебных токенов OpenAI.

    :param context: контекст для отправки в OpenAI
    :param model: модель GPT для подсчёта
    :param json_scheme: json-схема запроса (None если не используется)
    :return: итоговое количество токенов включая запас
    """

    # Получаем энкодер для модели
    encoding = checking_relevance_model_name(model=model)

    # Проверяем тип данных аргумента context
    context = checking_type_data_context(context=context)

    # Фиксируем длину контекста до преобразования
    original_context_len = len(context)

    # Преобразуем context в строку
    context_str = prepares_text_for_counting(context=context)

    # Считаем токены в контексте
    context_token_count = count_tokens(entity_count=context_str, encoding=encoding)

    # Проверяем наличие json-схемы
    if json_scheme is None:
        json_count = 0
    else:
        # Проверяем тип данных аргумента json_scheme
        json_scheme = checking_type_data_json_scheme(json_scheme=json_scheme)

        # Преобразуем json_scheme в строку
        json_scheme_str = prepares_json_for_counting(json_scheme=json_scheme)

        # Считаем токены в json-схеме
        json_count = count_tokens(entity_count=json_scheme_str, encoding=encoding)

    # Примерные скрытые служебные токены OPENAI
    service_tokens = (original_context_len + ADD_INDENTATION) * HEADER_TOKENS_COUNT

    # Считаем итоговое количество токенов
    result_token_count = context_token_count + json_count + service_tokens

    # Возвращаем сумму количества токенов в запросе с добавочными токенами
    return result_token_count + ADD_TOKENS_FOR_STOCK
