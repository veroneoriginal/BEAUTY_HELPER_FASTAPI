# apps/content_generation/openai/limiter/limiter_errors.py


class LimiterTargetException(Exception):
    """
    Limiter — ошибка формата target.
    Возникает когда передан неподдерживаемый тип генерации (не 'text' и не 'imagine').
    """


class LimiterChooseAccountException(Exception):
    """
    Limiter — ошибка выбора аккаунта.
    Возникает когда за максимальное количество попыток не удалось найти
    аккаунт с доступными лимитами RPM/TPM/IPM.
    """


class LimiterRedisUnavailableException(Exception):
    """
    Limiter — Redis недоступен.
    Возникает когда не удаётся прочитать или записать данные в Redis.
    """
