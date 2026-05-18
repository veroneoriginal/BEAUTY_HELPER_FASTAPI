# apps/content_generation/openai/utils/utils.py

from decimal import ROUND_UP, Decimal
from typing import Literal

from openai import OpenAI
from openai.types.chat import (
    ChatCompletion,
)

from apps.content_generation.openai.utils.utils_errors import (
    OpenAIGenTextContentException,
)


def generate_text_content_openai(
        api_key: str,
        context: list,
        settings: dict,
        model: Literal["gpt-4o-mini", "gpt-3.5-turbo"],
        json_scheme: dict,
) -> ChatCompletion:
    """
    Функция для отправки запроса на генерацию контента в OpenAI.

    :param api_key: Ключ доступа к аккаунту
    :param context: контекст запроса
    :param settings: настройки для запроса
    :param model: название модели OpenAI, которая будет использована для генерации
    :param json_scheme: json-схема запроса

    :return: объект ChatCompletion
    """
    try:
        client = OpenAI(api_key=api_key)

        tools = []
        if json_scheme:
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": json_scheme["name"],
                        "parameters": json_scheme["schema"]
                    }
                }
            ]

        return client.chat.completions.create(
            model=model,
            messages=context,
            temperature=settings['temperature'],
            max_tokens=settings['max_tokens'],
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
            tools=tools if tools else None,
        )

    except Exception as exc:
        raise OpenAIGenTextContentException(
            "Ошибка обработки запроса в OpenAI API"
        ) from exc


def to_decimal(price: float | int) -> Decimal:
    """
    Приводит число (стоимость) к Decimal с высокой точностью дробной части.

    :param price: Стоимость запроса, ответа или соотношение доллара к рублю
    :return: стоимость в формате Decimal с высокой точностью дробной части.
    """
    decimal_precision = Decimal('1e-15')

    return Decimal(str(price)).quantize(decimal_precision, rounding=ROUND_UP)
