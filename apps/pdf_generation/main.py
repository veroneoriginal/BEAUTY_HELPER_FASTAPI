# apps/pdf_generation/main.py

import asyncio

from apps.pdf_generation.creator_logic.main import (
    PDFCreator,
)
from apps.pdf_generation.pdf_data_processing.main import (
    PDFDataProcessor,
)
from apps.pdf_generation.utils import create_object_key
from apps.selection.models import SelectionTaskType
from infrastructure.s3.service import S3Service


def generate_selection_pdf(
        product_data: dict,
        analys: dict,
        task_type: SelectionTaskType,
) -> str | None:
    """
    Общая функция с логикой генерации PDF.
    Результат выполнения - ссылка на готовую PDF.

    :param product_data: DTO-продукта, преобразованный в словарь
    :param analys: информация от OpenAI о подборке
    :param task_type: тип задачи, по которой создается подборка
    :return: ссылка на готовую PDF
    """

    # 1. Берем задачу, данные о средстве product_data и analys продукта
    # и готовим данные для передачи в PDFCreator
    pdf_data_processor = PDFDataProcessor(
        task_type=task_type,
        analys=analys,
        product_data=product_data,
    )
    result = pdf_data_processor.process_data_with_task_code()
    # apps/pdf_generation/debug_data/pdf_docs_data.py

    # 2. Идём на S3 и получаем картинку/изображение
    s3 = S3Service()
    image_in_bytes = asyncio.run(s3.get_file(product_data["image_key"]))["file_bytes"]

    # 3. Генерируем pdf
    pdf_creator = PDFCreator(
        data_for_pdf=result,
        image_in_bytes=image_in_bytes,
    )
    bytes_pdf = pdf_creator.create_pdf()

    # 4. Генерируем ключ/название, под которым будет храниться pdf
    s3_key = create_object_key(
        prefix="pdf",
        extension="pdf",
        task_type=task_type,
        article=product_data['article_ga'],
    )

    # 5. Созданную PDF в виде bytes загружаем на S3.
    upload_pdf = asyncio.run(s3.upload_file(
        file_data=bytes_pdf,
        object_key=s3_key,
        extension="pdf",
    )
    )

    if upload_pdf["status_code"] == 200:
        # Генерируем ссылку на файл
        return f"{s3.endpoint_url}/{s3.bucket_name}/{s3_key}"

    return None
