# apps/content_generation/main_manage_class.py

from typing import Callable

from apps.content_generation.openai.main_openai import (
    OpenAIClient,
)


class GenerationManager:
    """
    Главный управляющий класс для взаимодействия со всей системой генерации контента.
    Принимает словарь с данными запроса, определяет сервис и вызывает нужный метод.

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
        Преобразует context из кортежа кортежей в список словарей
        необходимый для отправки запроса в OpenAI API.
        """

        # Фомирование списка для преобразования параметра context
        context_from_user = []

        # получаем кортеж кортежей
        messages = self.data["context"]

        for role, text in messages:
            context_from_user.append(
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
        self.data["context"] = context_from_user

    def _generate_text_with_openai(
            self,
    ) -> dict:
        """
        Отправляет запрос на генерацию текстового ответа от OpenAI.

        :return: ответ от OpenAI в виде словаря
        """

        return self.openai.main_request(request_details=self.data)

    def process_request(
            self,
    ) -> dict:
        """
        Главный метод класса.
        Преобразует запрос и вызывает метод соответствующий сервису и типу контента.

        :return: результат генерации в виде словаря
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
