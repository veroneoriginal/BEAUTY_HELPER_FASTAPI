# Smoke-тесты оркестрации generate_selection_pdf.
# Тяжёлые внутренности (обработка данных, ReportLab, S3) замоканы — проверяем
# склейку шагов: скачивание картинки, генерацию байтов, загрузку и сборку URL,
# а также корректную обработку сбоев S3.

import contextlib
from unittest.mock import AsyncMock, patch

import pytest

from apps.pdf_generation import main as pdf_main
from apps.selection.models import SelectionTaskType

PRODUCT_DATA = {"image_key": "images/x.jpg", "article_ga": "A123"}
ANALYS = {}


@contextlib.contextmanager
def patched_pdf(get_file_ret, upload_ret):
    """Подменяет обработчик данных, ReportLab-создатель, ключ и S3 на моки."""
    with (
        patch.object(pdf_main, "PDFDataProcessor") as pdp,
        patch.object(pdf_main, "PDFCreator") as creator,
        patch.object(pdf_main, "create_object_key", return_value="pdf/xyz.pdf"),
        patch.object(pdf_main, "S3Service") as s3cls,
    ):
        pdp.return_value.process_data_with_task_code.return_value = []
        creator.return_value.create_pdf.return_value = b"%PDF-1.4 fake"
        s3 = s3cls.return_value
        s3.endpoint_url = "http://s3"
        s3.bucket_name = "bucket"
        s3.get_file = AsyncMock(return_value=get_file_ret)
        s3.upload_file = AsyncMock(return_value=upload_ret)
        yield s3


def test_returns_url_on_successful_upload():
    """При успешной загрузке возвращается ссылка вида endpoint/bucket/key."""
    with patched_pdf(
        get_file_ret={"file_bytes": b"img", "error": None, "status_code": 200},
        upload_ret={"status_code": 200, "etag": "e", "error": None},
    ):
        url = pdf_main.generate_selection_pdf(
            product_data=PRODUCT_DATA,
            analys=ANALYS,
            task_type=SelectionTaskType.COMPOSITION_ANALYSIS,
        )
    assert url == "http://s3/bucket/pdf/xyz.pdf"


def test_returns_none_when_upload_fails():
    """Если загрузка вернула не-200 статус — функция возвращает None."""
    with patched_pdf(
        get_file_ret={"file_bytes": b"img", "error": None, "status_code": 200},
        upload_ret={"status_code": 500, "etag": None, "error": "boom"},
    ):
        url = pdf_main.generate_selection_pdf(
            product_data=PRODUCT_DATA,
            analys=ANALYS,
            task_type=SelectionTaskType.COMPOSITION_ANALYSIS,
        )
    assert url is None


def test_raises_when_image_download_fails():
    """Сбой скачивания картинки из S3 даёт понятную RuntimeError, а не KeyError."""
    with patched_pdf(
        get_file_ret={"status_code": None, "etag": None, "error": "S3 недоступен"},
        upload_ret={"status_code": 200},
    ):
        with pytest.raises(RuntimeError):
            pdf_main.generate_selection_pdf(
                product_data=PRODUCT_DATA,
                analys=ANALYS,
                task_type=SelectionTaskType.COMPOSITION_ANALYSIS,
            )
