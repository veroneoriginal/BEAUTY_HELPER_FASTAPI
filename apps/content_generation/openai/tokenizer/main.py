# apps/content_generation/openai/tokenizer/main.py
import json
from typing import Dict, List, Literal

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
    Функция, проверяющая тип данных контекста, который по итогу считаем.

    :param context: Контекст для отправки в OPENAI
    :return: список словарей
    """

    if not isinstance(context, list):
        raise TypeError(f"Аргумент {context} должен быть списком, "
                        f"а не {type(context).__name__}.")

    if not all(isinstance(item, dict) for item in context):
        raise TypeError("Все элементы списка должны быть словарями.")

    return context


def checking_type_data_json_scheme(
        json_scheme: dict,
) -> dict:
    """
    Проверяет, что json_scheme — это словарь, как ожидается.

    :param json_scheme: json-схема для отправки в OpenAI
    :return: тот же словарь, если всё ок
    """

    if not isinstance(json_scheme, dict):
        raise TypeError(f"Аргумент json_scheme должен быть словарём, "
                        f"а не {type(json_scheme).__name__}.")

    return json_scheme


def checking_relevance_model_name(
        model: Literal["gpt-4o-mini",],
) -> tiktoken.Encoding:
    """
    Функция подбирает энкодер для заданной модели GPT.

    :param model: Имя модели GPT, для которой нужно получить энкодер
    и с помощью которой идет анализ данных

    :return: Объект токенизации tiktoken.Encoding для указанной модели.
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
    Функция для преобразования атрибута context в строку.

    :param context: контекст для отправки в OPENAI.
    :return: контекст в виде строки
    """

    # Инициализируем переменную для объединения всех текстовых сообщений
    full_text_list = []

    # Проходим по каждому словарю в списке content
    for message in context:
        # Проверяем, есть ли ключ 'content' в словаре
        if 'content' in message:
            full_text_list.append(message['content'])

    result_list = []

    for item in full_text_list:
        for elements_dict in item:
            result_list.append(elements_dict['text'])

    return ' '.join(result_list)


def prepares_json_for_counting(
        json_scheme: dict,
) -> str:
    """
    Функция для преобразования json_scheme в строку.

    :param json_scheme: json_scheme для отправки в OPENAI.
    :return: контекст в виде строки
    """

    return json.dumps(json_scheme, ensure_ascii=False)


def count_tokens(
        entity_count: str,
        encoding: tiktoken.Encoding,
) -> int:
    """
    Функция для подсчета количества токенов в контексте/json-схеме.

    :param entity_count: сущность, которую нужно посчитать
    :param encoding: объект, который знает, как разбивать строки на токены,
    по правилам конкретной модели

    :return: количество токенов в тексте (числом)
    """

    # считаем токены, возвращаем полученный результат
    return len(encoding.encode(entity_count))


def main_count_tokens(
        context: List[Dict[str, str]],
        model: Literal["gpt-4o-mini",],
        json_scheme: dict | None,
) -> int:
    """
    Главная функция модуля для подсчета количества токенов в контексте и json-схеме.

    :param context: контекст для отправки в OPENAI, который нужно посчитать
    :param model: модель GPT, с помощью которой идет анализ данных
    :param json_scheme: json-схема запроса для отправки в OPENAI, которую нужно посчитать
    :return: количество токенов в контексте (число)
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
