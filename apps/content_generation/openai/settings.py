# apps/content_generation/openai/settings.py
# данные для модели 4о-mini


import os

from core.config import settings

OPENAI_ACCOUNT_1 = 'account_1'
OPENAI_ACCOUNT_2 = 'account_2'

SETTINGS_FOR_OPENAI_RESPONSE = {
    'temperature': 1,
    'max_tokens': 2048,
    'cost': {
        'USD_TO_RUB': 79.89,
        'PRICE_ONE_TOKEN_PROMPT_USD': 0.00000015,
        'PRICE_ONE_TOKEN_RESPONSE_USD': 0.000000075,
    }
}

ACCOUNT_LIMITS = {
    OPENAI_ACCOUNT_1: {
        'RPM': 300, # Requests Per Minute — количество запросов в минуту - 500 реально
        'TPM': 150000, # Tokens Per Minute — количество токенов в минуту - 200 000 реально
        'IPM': 0, # Images Per Minute — количество картинок в минуту
    },
    OPENAI_ACCOUNT_2: {
        'RPM': 300,
        'TPM': 150000,
        'IPM': 0,
    }
}

STORE_CURRENT_REQUEST = {
    OPENAI_ACCOUNT_1: {
        'RPM': 0,
        'TPM': 0,
        'IPM': 0,
    },
    OPENAI_ACCOUNT_2: {
        'RPM': 0,
        'TPM': 0,
        'IPM': 0,
    }
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
