# apps/pdf_generation/creator_logic/main.py
import os
import tempfile

from apps.pdf_generation.creator_logic.creator.document_creator import (
    TEMPLATE_CLASS,
    PDFFlowablesCreator,
    PDFPageTemplateandFrameBuilder,
)


class PDFCreator:
    """
    Создаёт PDF-документ и изображения из них
    """

    def __init__(
            self,
            data_for_pdf: list,
            image_in_bytes: bytes,
    ):
        """
        :param data_for_pdf: список с данными для генерации PDF
        :param image_in_bytes: изображение средства, которая хранится на S3
        """
        self.data_for_pdf = data_for_pdf
        self.image_in_bytes = image_in_bytes

    def create_pdf(self) -> bytes:
        """
        Создаёт PDF-документ из входящих данных и возвращает байты PDF.

        :return: Байты PDF
        """

        # 1. Создаём временный файл для PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:

            # Абсолютный путь до файла
            pdf_path = tmp_file.name

        try:
            # 2. Итерируемся по data-шагам
            for data in self.data_for_pdf:
                template_class = TEMPLATE_CLASS[data['Класс шаблона']]

                # Создаём документ
                doc = template_class(
                    filename=pdf_path,
                    path_to_brandline_file=data['Путь к изображению бренд-линии'],
                    doc_width_height=(
                        data['Размеры документа'][0],
                        data['Размеры документа'][1]
                    ),
                    brand_line_width_height=(
                        data['Размеры бренд-линии'][0],
                        data['Размеры бренд-линии'][1]
                    ),
                    brand_line_coords=data['Координаты вставки бренд-линии']
                )

                # Создаём flowables-элементы документа
                pdf_flowables_creator = PDFFlowablesCreator(
                    data=data,
                    image_in_bytes=self.image_in_bytes,
                )
                flowables = pdf_flowables_creator.create_flowables()

                # Создаём шаблоны страниц с фреймами
                page_templates_builder = PDFPageTemplateandFrameBuilder()
                templates = page_templates_builder.create_doc_templates(
                    templates_data=data['Шаблоны страниц с фреймами']
                )

                # добавление шаблона страницы в документ
                doc.addPageTemplates(templates)

                # рендер PDF-документа
                doc.build(flowables)

            # 3. Читаем PDF как bytes
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()

            # возвращаем bytes
            return pdf_bytes

        finally:
            # 4. Удаляем временный файл
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
