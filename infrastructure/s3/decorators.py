from functools import wraps

from botocore.exceptions import BotoCoreError, ClientError, EndpointConnectionError


def s3_safe_call(func):
    """
    Асинхронный декоратор для методов S3Service.
    Перехватывает ошибки boto3/botocore и возвращает стандартный словарь
    вместо выброса исключения.

    Подходит для методов, возвращающих dict с ключами:
    - status_code: HTTP-статус ответа от S3
    - etag: идентификатор версии объекта
    - error: None если успех, иначе строка с описанием ошибки
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except (EndpointConnectionError, ClientError, BotoCoreError) as e:
            return {
                "status_code": None,
                "etag": None,
                "error": f"S3 недоступен: {e}",
            }
        except Exception as e:
            return {
                "status_code": None,
                "etag": None,
                "error": f"Неизвестная ошибка: {e}",
            }
    return wrapper
