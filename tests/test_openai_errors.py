# Тесты распознавания ошибок OpenAI в generate_text_content_openai без сети.
# Клиент OpenAI подменён: create бросает нужную ошибку SDK, проверяем,
# во что она превращается — от этого зависит, повторит ли Celery задачу.

from unittest.mock import MagicMock, patch

import httpx
import openai
import pytest

from apps.content_generation.openai.utils import utils
from apps.content_generation.openai.utils.utils_errors import (
    OpenAIAuthError,
    OpenAIGenTextContentException,
    OpenAIInsufficientQuotaError,
)

SETTINGS = {"temperature": 1, "max_tokens": 4096, "timeout": 60}
REQUEST = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")


def _status_error(error_class, status: int, code: str | None = None):
    """
    Ошибка SDK с HTTP-статусом и кодом в теле ответа, как её бросает OpenAI.
    """
    return error_class(
        "error",
        response=httpx.Response(status, request=REQUEST),
        body={"code": code} if code else None,
    )


def _call(error=None) -> MagicMock:
    """
    Вызывает generate_text_content_openai с подменённым клиентом,
    возвращает мок класса OpenAI.
    """
    client_class = MagicMock()
    if error:
        client_class.return_value.chat.completions.create.side_effect = error
    with patch.object(utils, "OpenAI", client_class):
        utils.generate_text_content_openai(
            api_key="key",
            context=[],
            settings=SETTINGS,
            model="gpt-4o-mini",
            json_scheme={},
        )
    return client_class


def test_client_gets_timeout():
    """
    Клиенту передаётся таймаут из настроек, а не 10 минут SDK по умолчанию.
    """
    client_class = _call()

    client_class.assert_called_once_with(api_key="key", timeout=60)


def test_insufficient_quota_is_quota_error():
    """
    429 с кодом insufficient_quota — кончились деньги, без повторов.
    """
    error = _status_error(openai.RateLimitError, 429, "insufficient_quota")

    with pytest.raises(OpenAIInsufficientQuotaError):
        _call(error)


def test_rate_limit_is_retryable_error():
    """
    Обычный 429 (лимит запросов) — общая ошибка, Celery повторит.
    """
    error = _status_error(openai.RateLimitError, 429, "rate_limit_exceeded")

    with pytest.raises(OpenAIGenTextContentException):
        _call(error)


@pytest.mark.parametrize(
    "error_class, status",
    [
        (openai.AuthenticationError, 401),
        (openai.PermissionDeniedError, 403),
    ],
)
def test_bad_key_is_auth_error(error_class, status):
    """
    Неверный ключ или нет доступа — своя ошибка, а не «кончились деньги».
    """
    with pytest.raises(OpenAIAuthError):
        _call(_status_error(error_class, status, "invalid_api_key"))


def test_timeout_is_retryable_error():
    """
    Таймаут — общая ошибка, Celery повторит.
    """
    with pytest.raises(OpenAIGenTextContentException):
        _call(openai.APITimeoutError(request=REQUEST))
