# Тест выбора настроек модели OpenAI по названию из OPENAI_MODEL.

import pytest

from apps.content_generation.openai.models import MODELS, get_model_settings


def test_known_model_returns_settings():
    """Модель из MODELS — возвращается её модуль с ценами и лимитами."""
    model_settings = get_model_settings("gpt-4o-mini")

    assert model_settings is MODELS["gpt-4o-mini"]
    assert model_settings.PRICE_ONE_TOKEN_RESPONSE_USD == 0.0000006


def test_unknown_model_raises():
    """Модели нет в MODELS — ошибка с её названием, а не цены по умолчанию."""
    with pytest.raises(ValueError, match="gpt-unknown"):
        get_model_settings("gpt-unknown")
