# apps/content_generation/openai/utils/utils.py

import logging
import time
from decimal import ROUND_UP, Decimal

import openai
from openai import OpenAI
from openai.types.chat import (
    ChatCompletion,
)

from apps.content_generation.openai.utils.utils_errors import (
    OpenAIAuthError,
    OpenAIGenTextContentException,
    OpenAIInsufficientQuotaError,
)

logger = logging.getLogger(__name__)


def generate_text_content_openai(
    api_key: str,
    context: list,
    settings: dict,
    model: str,
    json_scheme: dict,
) -> ChatCompletion:
    """
    Отправляет запрос на генерацию текстового контента в OpenAI.

    :param api_key: Ключ доступа к аккаунту OpenAI
    :param context: контекст запроса в формате списка словарей
    :param settings: настройки запроса (temperature, max_tokens, timeout)
    :param model: название модели OpenAI
    :param json_scheme: json-схема для structured output

    :return: объект ChatCompletion с ответом от OpenAI
    :raises OpenAIInsufficientQuotaError: на аккаунте кончились деньги
    :raises OpenAIAuthError: неверный ключ или нет доступа
    :raises OpenAIGenTextContentException: остальные ошибки — их можно повторить
    """
    try:
        # Без timeout SDK ждёт ответа до 10 минут
        client = OpenAI(api_key=api_key, timeout=settings["timeout"])

        tools = []
        if json_scheme:
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": json_scheme["name"],
                        "strict": json_scheme.get("strict", False),
                        "parameters": json_scheme["schema"],
                    },
                }
            ]

        started = time.monotonic()
        response = client.chat.completions.create(
            model=model,
            messages=context,
            temperature=settings["temperature"],
            max_tokens=settings["max_tokens"],
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
            tools=tools if tools else None,
        )
        # Время одного запроса — по нему подбираем таймаут клиента
        logger.info(
            "[OPENAI] Запрос к %s: %.1f сек, токенов запрос/ответ %s/%s",
            model,
            time.monotonic() - started,
            response.usage.prompt_tokens,
            response.usage.completion_tokens,
        )
        return response

    except openai.RateLimitError as exc:
        # 429 бывает двух видов: кончились деньги (повтор не поможет)
        # и обычный лимит запросов (повтор через несколько секунд пройдёт)
        if exc.code == "insufficient_quota":
            raise OpenAIInsufficientQuotaError(
                "Недостаточно средств на балансе OpenAI"
            ) from exc
        raise OpenAIGenTextContentException("Превышен лимит запросов OpenAI") from exc
    except (openai.AuthenticationError, openai.PermissionDeniedError) as exc:
        raise OpenAIAuthError(
            "Неверный ключ OpenAI или нет доступа к аккаунту"
        ) from exc
    except Exception as exc:
        raise OpenAIGenTextContentException(
            "Ошибка обработки запроса в OpenAI API"
        ) from exc


def to_decimal(price: float | int) -> Decimal:
    """
    Приводит число (стоимость) к Decimal с высокой точностью дробной части.
    Используется для расчёта стоимости запросов к OpenAI.

    :param price: стоимость в float или int
    :return: стоимость в формате Decimal с точностью 1e-15 (дробной части)
    """
    decimal_precision = Decimal("1e-15")

    return Decimal(str(price)).quantize(decimal_precision, rounding=ROUND_UP)
