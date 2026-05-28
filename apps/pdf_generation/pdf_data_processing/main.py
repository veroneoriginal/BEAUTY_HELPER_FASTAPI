# apps/pdf_generation/pdf_data_processing/main.py

from apps.pdf_generation.pdf_data_processing.tasks_logic.detailed_analysis_composition import (
    DetailedAnalysisCompositionPDFTemplateCreator,
)
from apps.pdf_generation.utils import (
    translate_keys_to_rus,
)
from apps.selection.models import (
    SelectionTaskType,
)


class PDFDataProcessor:
    """
    Класс для подготовки данных к передаче в PDFCreator
    """

    def __init__(
        self,
        product_data: dict,
        analys: dict,
        task_type: SelectionTaskType,
    ) -> None:
        """
        :param product_data: DTO-продукта, преобразованный в словарь
        :param analys: информация от OpenAI о подборке
        :param task_type: тип задачи, по которой создается подборка
        """
        self.product_data = product_data
        self.analys = analys
        self.task_type = task_type

        self.method_for_task_code = {
            SelectionTaskType.COMPOSITION_ANALYSIS: self.detailed_analysis_composition,
        }

    def process_data_with_task_code(self):
        """
        Вызывает нужную логику в зависимости от кода задачи.
        Возвращает словарь с готовой полной информацией по подборке,
        для передачи в PDFCreator для создания PDF и изображений.

        :return: Список с итоговыми данными для создания PDF. Каждый элемент списка -
        словарь с данными для создания документа.
        """
        return self.method_for_task_code[self.task_type]()

    def detailed_analysis_composition(self):
        """
        Задача "Подробный анализ каждого элемента состава"
        """

        # Переводим словарь с английскими ключами на русский язык
        analys_translate_to_russian = translate_keys_to_rus(self.analys)

        # готовим данные для PDF-документа по этой конкретной задаче
        detailed_analysis_pdf = DetailedAnalysisCompositionPDFTemplateCreator(
            product_data=self.product_data,
            translated_analys=analys_translate_to_russian,
        )

        return detailed_analysis_pdf.get_data_for_pdf_docs()
