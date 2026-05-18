# apps/content_generation/main_manage_class.py
from typing import Callable

from apps.content_generation.openai.main_openai import (
    OpenAIClient,
)


class GenerationManager:
    """
    Главный управляющий класс для взаимодействия со всей системой генерации контента.

    :param data_request: словарь с данными запроса из бизнес-логики в следующем виде
    {
            'service': "openai",
            'model': "gpt-4o-mini",
            'target': "text",
            'context': (
            ('system', 'Ты профессиональный эксперт по косметике с медицинским образованием'),
            ('user', 'Напиши о том, как правильно ухаживать за собой женщине в 31 год'),
            ),
            'pictures': None,
        }
    """

    def __init__(
            self,
            data_request: dict,
    ):
        # Инициализация доступных сервисов
        self.services: dict[tuple[str, str], Callable] = {
            ("text", "openai"): self._generate_text_with_openai,
        }

        self.data = data_request
        self.openai = OpenAIClient()

    def _convert_user_request(self) -> None:
        """
        Метод для преобразования self.data в список словарей
        и обновления в текущем словаре запроса, который по итогу отправляется на API.

        """

        # Фомирование списка для преобразования параметра context
        CONTEXT_FROM_USER = []

        # получаем кортеж кортежей
        messages = self.data["context"]

        for role, text in messages:
            CONTEXT_FROM_USER.append(
                {"role": role,
                 "content": [
                     {
                         "type": "text",
                         "text": text,
                     },
                 ],
                 },
            )

        # в исходном словаре обновляем значение по ключу messages
        self.data["context"] = CONTEXT_FROM_USER

    def _generate_text_with_openai(
            self,
    ) -> dict:
        """
        Метод для генерации текстового ответа от OpenAI.
        :return: ответ от API
        """

        # отправляю запрос и получаю ответ от OPENAI
        return self.openai.main_request(request_details=self.data)

    def process_request(
            self,
    ) -> dict:
        """
        Метод для обработки запроса и вызова метода, соответствующего запросу.

        :return: результат генерации в виде словаря.
        """

        # Преобразовываем словарь запроса
        self._convert_user_request()

        # Ищем соответствующий обработчик в self.services
        key = (
            self.data.get("target"),
            self.data.get("service"),
        )

        # Вызываем метод, соответствующий target и service
        return self.services[key]()
