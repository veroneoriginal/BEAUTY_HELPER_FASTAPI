# apps/content_generation/openai/models/gpt_4o_mini.py
# данные для модели gpt-4o-mini

# Параметры запроса
TEMPERATURE = 1
MAX_TOKENS = 4096

# Сколько ждать ответа на один запрос, секунд. Замер 15.10: шаг с ответом
# ~970 токенов — 11 с; даже MAX_TOKENS (~90 токенов/с) — ~45 с
TIMEOUT_SECONDS = 60

# Цены за один токен, USD (0.15 $ и 0.60 $ за миллион)
PRICE_ONE_TOKEN_PROMPT_USD = 0.00000015
PRICE_ONE_TOKEN_RESPONSE_USD = 0.0000006

# Лимиты одного аккаунта в минуту
LIMITS = {
    "RPM": 300,  # Requests Per Minute — количество запросов в минуту - 500 реально
    "TPM": 150000,  # Tokens Per Minute — количество токенов в минуту - 200 000 реально
    "IPM": 0,  # Images Per Minute — количество картинок в минуту
}
