# apps/content_generation/openai/utils/utils_errors.py

class OpenAIGenTextContentException(Exception):
    """
    OpenAI ошибка генерации тестового контента
    """

    def __str__(self):
        return "OpenAIGenTextContentException: Ошибка запроса при обращении к OpenAI"


class OpenAIInsufficientQuotaError(Exception):
    """
    Фатальная ошибка: у аккаунта OpenAI закончилась квота
    """
