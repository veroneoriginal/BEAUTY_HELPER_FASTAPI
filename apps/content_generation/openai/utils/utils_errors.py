# apps/content_generation/openai/utils/utils_errors.py


class OpenAIGenTextContentException(Exception):
    """
    Ошибка генерации текстового контента через OpenAI API.
    Возникает при любой ошибке во время отправки запроса или получения ответа.
    """

    def __str__(self):
        return "OpenAIGenTextContentException: Ошибка запроса при обращении к OpenAI"


class OpenAIInsufficientQuotaError(Exception):
    """
    Фатальная ошибка: у аккаунта OpenAI закончилась квота.
    Требует пополнения баланса или смены аккаунта.
    """
