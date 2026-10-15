# apps/content_generation/openai/settings.py
# Цены, лимиты и параметры запроса берутся из файла модели в models/
# по OPENAI_MODEL; неизвестная модель — ошибка при старте

from apps.content_generation.openai.models import get_model_settings
from core.config import settings

MODEL_SETTINGS = get_model_settings(settings.OPENAI_MODEL)

OPENAI_ACCOUNT_1 = "account_1"
OPENAI_ACCOUNT_2 = "account_2"

SETTINGS_FOR_OPENAI_RESPONSE = {
    "temperature": MODEL_SETTINGS.TEMPERATURE,
    "max_tokens": MODEL_SETTINGS.MAX_TOKENS,
    "timeout": MODEL_SETTINGS.TIMEOUT_SECONDS,
    "cost": {
        "USD_TO_RUB": settings.OPENAI_USD_TO_RUB,
        "PRICE_ONE_TOKEN_PROMPT_USD": MODEL_SETTINGS.PRICE_ONE_TOKEN_PROMPT_USD,
        "PRICE_ONE_TOKEN_RESPONSE_USD": MODEL_SETTINGS.PRICE_ONE_TOKEN_RESPONSE_USD,
    },
}

# Лимиты у аккаунтов одинаковые — из файла модели
ACCOUNT_LIMITS = {
    OPENAI_ACCOUNT_1: dict(MODEL_SETTINGS.LIMITS),
    OPENAI_ACCOUNT_2: dict(MODEL_SETTINGS.LIMITS),
}

STORE_CURRENT_REQUEST = {
    OPENAI_ACCOUNT_1: {
        "RPM": 0,
        "TPM": 0,
        "IPM": 0,
    },
    OPENAI_ACCOUNT_2: {
        "RPM": 0,
        "TPM": 0,
        "IPM": 0,
    },
}

# Ключи берем из core.config
ACCOUNT_KEYS = {
    OPENAI_ACCOUNT_1: settings.OPENAI_API_KEY_ACCOUNT_ONE,
    OPENAI_ACCOUNT_2: settings.OPENAI_API_KEY_ACCOUNT_TWO,
}
# цена в токенах за каждый абзац
HEADER_TOKENS_COUNT = 4

# добавочный абзац, который добавляет GPT
ADD_INDENTATION = 1

# токены для запаса, чтобы не возникло проблем с лимитером
ADD_TOKENS_FOR_STOCK = 5
