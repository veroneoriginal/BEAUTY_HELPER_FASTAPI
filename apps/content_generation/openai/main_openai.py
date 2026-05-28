# apps/content_generation/openai/main_openai.py
import json
import traceback
from typing import (
    Dict,
    Literal,
    Optional,
)

from openai.types.chat import (
    ChatCompletion,
)

from apps.content_generation.openai.key_manager.main import (
    KeyManager,
)
from apps.content_generation.openai.settings import (
    SETTINGS_FOR_OPENAI_RESPONSE,
)
from apps.content_generation.openai.tokenizer.main import (
    main_count_tokens,
)
from apps.content_generation.openai.utils.utils import (
    generate_text_content_openai,
    to_decimal,
)
from apps.content_generation.openai.utils.utils_errors import (
    OpenAIGenTextContentException,
)


class OpenAIClient:
    """
    Класс для управления запросами к OpenAI API.
    Получает ключ доступа через KeyManager, считает токены,
    отправляет запрос и возвращает структурированный ответ.
    """

    def __init__(self):

        self.settings = SETTINGS_FOR_OPENAI_RESPONSE
        self.key_manager = KeyManager()

    @staticmethod
    def _generate_if_failed(
        exception: Optional[Exception],
    ) -> Dict:
        """
        Формирует словарь с информацией об ошибке.

        :param exception: исключение которое произошло
        :return: словарь с ключами status, message, error, cost_interaction, exception, traceback
        """

        return {
            "status": "failed",
            "message": "Ошибка запроса при обращении к OpenAI",
            "error": True,
            "cost_interaction": None,
            "exception": str(exception),
            "traceback": traceback.format_exc(),
        }

    def _extract_content(
        self,
        response: ChatCompletion,
    ) -> str:
        """
        Извлекает контент из объекта ChatCompletion.
        Парсит аргументы tool_call как JSON.

        :param response: объект ChatCompletion от OpenAI
        :return: распарсенный JSON-ответ
        """

        # response.choices[0].message

        tool_call = response.choices[0].message.tool_calls[0]
        return json.loads(tool_call.function.arguments)

    def calculates_cost(
        self,
        response: ChatCompletion,
    ) -> Dict:
        """
        Рассчитывает стоимость запроса в USD и RUB.

        :param response: объект ChatCompletion от OpenAI
        :return: словарь со стоимостью prompt, completion и total в токенах, USD и RUB
        """

        # prompt_tokens: Количество токенов в запросе
        prompt_tokens = response.usage.prompt_tokens

        # completion_tokens: Количество токенов в ответе
        completion_tokens = response.usage.completion_tokens

        # общее количество токенов
        total_tokens = prompt_tokens + completion_tokens

        # Получаем словарь с ценами
        dict_with_price = self.settings["cost"]

        # Преобразуем цены и курс в Decimal
        price_one_token_prompt_usd = to_decimal(
            dict_with_price["PRICE_ONE_TOKEN_PROMPT_USD"]
        )
        price_one_token_completion_usd = to_decimal(
            dict_with_price["PRICE_ONE_TOKEN_RESPONSE_USD"]
        )
        usd_to_rub = to_decimal(dict_with_price["USD_TO_RUB"])

        # Рассчитываем стоимость токенов запроса (prompt)
        prompt_cost_usd = to_decimal(prompt_tokens) * price_one_token_prompt_usd
        prompt_cost_rub = prompt_cost_usd * usd_to_rub

        # Рассчитываем стоимость токенов ответа (completion)
        completion_token_cost_usd = (
            to_decimal(completion_tokens) * price_one_token_completion_usd
        )
        completion_cost_rub = completion_token_cost_usd * usd_to_rub

        # Общая стоимость
        total_cost_usd = prompt_cost_usd + completion_token_cost_usd
        total_cost_rub = total_cost_usd * usd_to_rub

        # словарь с количеством токенов и их ценами в долларах и рублях
        return {
            "prompt": {
                "prompt_tokens": prompt_tokens,
                "USD": prompt_cost_usd,
                "RUB": prompt_cost_rub,
            },
            "completion": {
                "completion_tokens": completion_tokens,
                "USD": completion_token_cost_usd,
                "RUB": completion_cost_rub,
            },
            "total": {
                "total_tokens": total_tokens,
                "USD": total_cost_usd,
                "RUB": total_cost_rub,
            },
        }

    def _generate_if_success(
        self,
        response: ChatCompletion,
    ) -> Dict:
        """
        Формирует словарь с успешным ответом от OpenAI.

        :param response: объект ChatCompletion от OpenAI
        :return: словарь с ключами status, message, error, cost_interaction
        """
        return {
            "status": "success",
            "message": self._extract_content(response),
            "error": False,
            "cost_interaction": self.calculates_cost(response),
        }

    def get_access_key(
        self,
        request_details: dict,
    ) -> str:
        """
        Считает токены запроса и получает ключ доступа через KeyManager.

        :param request_details: словарь с данными запроса
        :return: API-ключ для отправки запроса
        """

        # количество токенов в этом контексте - int
        count_tokens = main_count_tokens(
            context=request_details["context"],
            model=request_details["model"],
            json_scheme=request_details["json_scheme"],
        )

        # обновляю значение в словаре
        request_details["count_tokens"] = count_tokens

        # возвращаю ключ доступа
        return self.key_manager.get_key(query_details=request_details)

    def send_text_request_to_openai(
        self,
        api_key: str,
        context: list,
        model: Literal["gpt-4o-mini"],
        json_scheme: dict,
    ) -> Dict:
        """
        Отправляет текстовый запрос в OpenAI API.

        :param api_key: ключ доступа к аккаунту
        :param context: контекст запроса
        :param model: название модели OpenAI
        :param json_scheme: JSON-схема для structured output
        :return: словарь с ответом от OpenAI
        """

        try:
            # если все хорошо, то в response - объект ChatCompletion
            response = generate_text_content_openai(
                api_key=api_key,
                context=context,
                settings=self.settings,
                model=model,
                json_scheme=json_scheme,
            )

            return self._generate_if_success(response=response)

        # если произошла ошибка -> словарь с другим содержимым
        except OpenAIGenTextContentException as exc:
            return self._generate_if_failed(exc)

    def main_request(
        self,
        request_details: dict,
    ) -> dict:
        """
        Главный метод, в котором: проверяем контент, получаем ключ доступа,
        отправляем реальный запрос на API.

        :param request_details: словарь с информацией о запросе
        request_details = {
            'service': 'openai',
            'model': 'gpt-4o-mini',
            'target': 'text',
            'json_scheme': {},
            'context':
                [
                    {'role': 'system',
                     'content': [
                         {
                             'type': 'text',
                             'text': 'Ты профессиональный эксперт по косметике с мед.образованием.',
                         }
                     ]
                     },

                    {'role': 'user',
                     'content': [
                         {
                             'type': 'text',
                             'text': 'Напиши о том, как правильно ухаживать за собой женщине
                              в 31 год',
                         }
                     ]
                     }
                ],
            'pictures': None}

        :return: ответ от OpenAI в виде словаря
        """

        if request_details["target"] != "text":
            return {
                "error": f"Неподдерживаемый тип таргета: {request_details['target']}"
            }

        # получаем ключ доступа
        access_key = self.get_access_key(request_details=request_details)

        # отправляю реальный запрос на API OPENAI
        return self.send_text_request_to_openai(
            context=request_details["context"],
            api_key=access_key,
            model=request_details["model"],
            json_scheme=request_details["json_scheme"],
        )
