# apps/orchestrator/utils.py

from uuid import uuid4

from apps.selection.models import SelectionTaskType


def create_object_key(
        prefix: str,
        extension: str,
        task_type: SelectionTaskType,
        article: str,
) -> str:
    """
    Генерирует ключ файла внутри S3 бакета.
    Ключ формируется снаружи S3-сервиса — S3 получает уже готовый ключ.

    :param prefix: название папки в бакете (например "pdfs")
    :param extension: расширение файла без точки (например "pdf")
    :param task_type: тип задачи подборки
    :param article: артикул продукта
    :return: строка вида "pdfs/detailed_analysis_19000002015_uuid.pdf"
    """
    return f"{prefix}/{task_type.value}_{article}_{uuid4()}.{extension.lower()}"
