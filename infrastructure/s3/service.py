import aioboto3
from core.config import settings
from infrastructure.s3.decorators import s3_safe_call


class S3Service:
    """
    Асинхронный сервис для работы с облачным хранилищем S3.
    Использует aioboto3 — async-обёртку над boto3.
    Клиент открывается и закрывается при каждом вызове через async with.
    """

    def __init__(self):
        self.bucket_name = settings.S3_BUCKET_NAME
        self.endpoint_url = settings.S3_ENDPOINT_URL
        self.session = aioboto3.Session(
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_KEY,
        )

    @s3_safe_call
    async def upload_file(
            self,
            file_data: bytes,
            object_key: str,
            extension: str,
    ) -> dict:
        """
        Загружает файл в S3.

        :param file_data: Байты файла (PDF и т.п.)
        :param object_key: Ключ файла внутри бакета, например: "pdfs/analysis_uuid.pdf"
        :param extension: Расширение файла без точки, например: "pdf"
        :return: Словарь с ключами:
            - status_code: HTTP-статус ответа от S3
            - etag: идентификатор версии объекта
            - error: None если успех, иначе строка с описанием ошибки
        """
        content_type = self._get_content_type(extension)

        async with self.session.client("s3", endpoint_url=self.endpoint_url) as s3:
            response = await s3.put_object(
                Bucket=self.bucket_name,
                Key=object_key,
                Body=file_data,
                ContentType=content_type,
            )

        status_code = response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0)

        if status_code != 200:
            return {
                "status_code": status_code,
                "etag": None,
                "error": f"Ошибка загрузки (status={status_code})",
            }

        # Успешная загрузка
        return {
            "status_code": status_code,
            "etag": response.get("ETag"),
            "error": None,
        }

    @s3_safe_call
    async def get_file(
            self,
            object_key: str,
    ) -> dict:
        """
        Получает файл из S3 по ключу.

        :param object_key: Ключ (путь) объекта внутри бакета, например: "pdfs/analysis_uuid.pdf"
        :return: Словарь с ключами:
            - status_code: HTTP-статус ответа от S3
            - etag: идентификатор версии объекта
            - error: None если успех, иначе строка с описанием ошибки
            - file_bytes: содержимое файла в виде bytes
        """
        async with self.session.client("s3", endpoint_url=self.endpoint_url) as s3:
            response = await s3.get_object(Bucket=self.bucket_name, Key=object_key)
            file_bytes = await response["Body"].read()

        status_code = response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0)

        return {
            "status_code": status_code,
            "etag": response.get("ETag"),
            "error": None,
            "file_bytes": file_bytes,
        }

    @s3_safe_call
    async def delete_file(
            self,
            object_key: str,
    ) -> dict:
        """
        Удаляет файл из S3 по ключу.

        :param object_key: Ключ (путь) объекта внутри бакета, например: "pdfs/analysis_uuid.pdf"
        :return: Словарь с ключами:
            - status_code: HTTP-статус ответа от S3
            - etag: None (S3 не возвращает etag при удалении)
            - error: None если успех, иначе строка с описанием ошибки
        """
        async with self.session.client("s3", endpoint_url=self.endpoint_url) as s3:
            response = await s3.delete_object(Bucket=self.bucket_name, Key=object_key)

        status_code = response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0)

        return {
            "status_code": status_code,
            "etag": None,
            "error": None if status_code == 204 else f"Неожиданный статус: {status_code}",
        }

    @staticmethod
    def _get_content_type(extension: str) -> str:
        """
        Возвращает MIME-тип по расширению файла.
        Если расширение неизвестно — возвращает "application/octet-stream".

        :param extension: Расширение файла без точки, например: "pdf"
        :return: MIME-тип строкой
        """
        return {
            "pdf": "application/pdf",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
        }.get(extension.lower(), "application/octet-stream")


# Объект создаётся один раз при старте приложения и переиспользуется всеми запросами. Принцип синглтон.
s3_service = S3Service()
