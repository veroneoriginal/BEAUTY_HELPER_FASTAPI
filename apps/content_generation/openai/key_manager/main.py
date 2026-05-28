# apps/content_generation/openai/key_manager/main.py

from apps.content_generation.openai.limiter.main import (
    Limiter,
)
from apps.content_generation.openai.settings import (
    ACCOUNT_KEYS,
)


class KeyManager:
    """
    Класс для получения ключа доступа к OpenAI API.
    Использует Limiter для выбора аккаунта с доступными лимитами,
    затем возвращает ключ этого аккаунта.
    """

    def __init__(self):
        self.limiter = Limiter()

        # Загружаем словарь, в котором хранятся ключи от аккаунтов
        self.account_keys = ACCOUNT_KEYS

    def get_key(
        self,
        query_details: dict,
    ) -> str:
        """
        Проверяет лимиты, выбирает доступный аккаунт и возвращает его ключ.

        :param query_details: словарь с содержимым запроса вида:
        {
            "service": "openai",
            "model": "gpt-4o-mini",
            "target": "text",
            "context": [...],
            "pictures": None,
            "count_tokens": 250,
        }
        :return: API-ключ выбранного аккаунта
        """

        name_account = self.limiter.main_get_account_name(query_details)

        # дальше обращаюсь к словарю и получаю ключ
        return self.account_keys[name_account]
