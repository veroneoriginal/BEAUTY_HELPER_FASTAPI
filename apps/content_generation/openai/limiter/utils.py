# apps/content_generation/openai/limiter/utils.py

from datetime import datetime, timezone

from redis import Redis

from apps.content_generation.openai.limiter.limiter_errors import (
    LimiterTargetException,
)


def get_connect_to_redis(
        host: str,
        port: int,
        db: int,
        password: str,
) -> Redis:
    """
    Функция создаёт и возвращает подключение к Redis.

    :param host: Адрес хоста Redis (например, '127.0.0.1' или имя сервиса в Docker)
    :param port: порт, на котором работает Redis (обычно 6379)
    :param db: номер базы данных Redis (по умолчанию 0)
    :param password: пароль

    :return: Объект подключения redis.Redis
    """

    return Redis(
        host=host,
        port=port,
        db=db,
        password=password,
    )


def generate_key_with_time() -> str:
    """
    Функция для генерации ключа с текущим временем запроса

    :return: строка с текущим временем
    """

    # Получаю текущее время и преобразовываю в строку
    return datetime.now(timezone.utc).strftime("openai_%d_%m_%y_%H_%M")


def calculate_time_to_next_minute() -> int:
    """
    Функция для вычисления времени (в секундах) до следующей минуты

    :return: остаток времени в секундах до следующей минуты
    """

    return 60 - datetime.now(timezone.utc).second


def creating_dict_with_info_from_query(
        query_details: dict,
) -> dict:
    """
    Функция для формирования словаря с лимитами на основе запроса.

    :param query_details: словарь с содержимым запроса
    :return: словарь с лимитами по ключам 'RPM', 'TPM', 'IPM':
             - RPM: Requests Per Minute
             - TPM: Tokens Per Minute
             - IPM: Images Per Minute
    """

    match query_details['target']:

        case "text":
            return {
                'RPM': 1,
                'TPM': query_details['count_tokens'],
                'IPM': 0,
            }

        case "imagine":
            return {
                'RPM': query_details['pictures'],
                'TPM': 0,
                'IPM': query_details['pictures'],
            }

        case _:
            raise LimiterTargetException(f"Неподдерживаемый таргет - {query_details['target']}")
