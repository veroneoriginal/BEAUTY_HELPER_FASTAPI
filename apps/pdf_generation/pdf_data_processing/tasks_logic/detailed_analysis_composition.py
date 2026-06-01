# apps/pdf_generation/pdf_data_processing/tasks_logic/detailed_analysis_composition.py

"""
Создание PDF-документов для задачи "Подробный анализ каждого элемента состава"
"""

from apps.pdf_generation.pdf_data_processing.tasks_logic.base_task import (
    get_base_info_by_product,
)
from apps.pdf_generation.utils import (
    calculate_price_per_standard_unit,
)
from core.assets import ORANGE_LIGHT_VERTICAL_BRAND_LINE_PATH

PDF_STRUCTURE = {
    "Базовая категория": {
        "Класс шаблона": "PDFBaseDocTemplateWithBrandLine",
        "Размеры бренд-линии": (85, 1280),
        "Координаты вставки бренд-линии": [
            (0, 0),
        ],
        "Размеры документа": (1024, 1280),  # (ширина, высота) в пикселях
        "Элементы и стили": [
            (
                "Image",
                {
                    "Ключ в подборке": "Путь к изображению средства",
                    "width": 1024,
                    "height": 1280,
                },
            ),
            ("Spacer", {"width": 1, "height": 34}),
            (
                "FreeText",
                {
                    "Ключ в подборке": "Артикул",
                    "x": 600,
                    "y": 666,
                    "font_name": "Montserrat-Regular",
                    "font_size": 14,
                    "font_color": "#000000FF",
                    "bold": False,
                    "align": "left",
                },
            ),
            (
                "FreeText",
                {
                    "Текст": "Правообладатель изображения: https://goldapple.ru/",
                    "x": -40,
                    "y": 54,
                    "font_name": "Montserrat-Regular",
                    "font_size": 10,
                    "font_color": "#1E1F2280",
                    "bold": False,
                    "align": "left",
                },
            ),
            (
                "Paragraph",
                {"Текст": "<b>Подробный разбор состава</b>", "Стиль": "ACOP_title_2"},
            ),
            ("Spacer", {"width": 1, "height": 40}),
            (
                "Paragraph",
                {"Ключ в подборке": "Тип продукта", "Стиль": "ACOP_normal_2"},
            ),
            ("Spacer", {"width": 1, "height": 26}),
            (
                "Paragraph",
                {"Ключ в подборке": "Название средства", "Стиль": "ACOP_title_1"},
            ),
            ("Spacer", {"width": 1, "height": 26}),
            (
                "Paragraph",
                {"Текст": "<b>Цена за средство:</b>", "Стиль": "ACOP_bold_2"},
            ),
            ("Spacer", {"width": 1, "height": 34}),
            (
                "Paragraph",
                {
                    "Ключ в подборке": "Количество мера / цена",
                    "Стиль": "ACOP_base_price_1",
                },
            ),
            ("Spacer", {"width": 1, "height": 54}),
            (
                "Paragraph",
                {"Текст": "<b>Соотношение цены:</b>", "Стиль": "ACOP_bold_2"},
            ),
            ("Spacer", {"width": 1, "height": 34}),
            (
                "Paragraph",
                {"Ключ в подборке": "Соотношение цены", "Стиль": "ACOP_price_ratio_1"},
            ),
            ("NextPageTemplate", {"template_id": "template_2"}),
            ("PageBreak", {}),
            # следующая страница
        ],
        "Шаблоны страниц с фреймами": {
            "template_1": (
                (
                    0,
                    (133, 0),
                    (794, 1288),
                ),  # Номер, Координаты левого нижнего угла, ширина и высота фрейма
            ),
            "template_2": (
                (0, (133, 85), (794, 1094)),
                # Номер, Координаты левого нижнего угла, ширина и высота фрейма
            ),
        },
    },
}


class DetailedAnalysisCompositionPDFTemplateCreator:
    """
    Готовит данные для PDF-документов по задаче
    "Подробный анализ каждого элемента состава" или SelectionTaskType.COMPOSITION_ANALYSIS
    """

    def __init__(
        self,
        product_data: dict,
        translated_analys: list | dict,
    ):
        """
        :param product_data: DTO - продукта, преобразованный в словарь
        :param translated_analys: информация от OpenAI о подборке в виде
        списка словарей, переведенная на русский язык
        """
        self.product_data = product_data
        self.translated_analys = translated_analys
        self.pdf_docs_data = []

    def get_data_for_pdf_docs(self) -> list:
        """
        Задача "Подробный анализ каждого элемента состава"
        :return: Возвращает список с данными для создания документов
        """

        template = self.get_base_template(one_product_data=self.translated_analys)
        self.pdf_docs_data.append(template)

        return self.pdf_docs_data

    def get_base_template(
        self,
        one_product_data: dict,
    ) -> dict:
        """
        Наполняет базовый шаблон PDF

        :param one_product_data: данные средства из ответа нейронки
        :return: словарь с информацией для создания PDF-документа
        """

        template_data = {
            "Соотношение цены": calculate_price_per_standard_unit(
                quantity=self.product_data["measure_value"],  # Количество меры (число)
                unit=self.product_data["measure_unit"],  # Юниты меры (мл/шт.)
                price_rub=self.product_data["price_rub"],  # Стоимость (руб.)
            ),
            "Путь к изображению бренд-линии": ORANGE_LIGHT_VERTICAL_BRAND_LINE_PATH,
            "Вывод": one_product_data.get("Вывод") or "Анализ состава выполнен.",
        }

        elements_data = self.get_composition_elements_data(
            one_product_data=one_product_data,
        )
        composition_elements_data_for_template = (
            self.get_composition_elements_data_for_template(
                one_product_data=one_product_data,
            )
        )

        base_product_data = get_base_info_by_product(
            product_data=self.product_data,
        )

        template_data.update(base_product_data)
        template_data.update(elements_data)
        template_data.update(PDF_STRUCTURE["Базовая категория"])
        template_data["Элементы и стили"] = list(template_data["Элементы и стили"])
        template_data["Элементы и стили"].extend(composition_elements_data_for_template)
        template_data["Элементы и стили"].extend(self.get_conclusion_page_elements())

        return template_data

    def get_composition_elements_data(
        self,
        one_product_data: dict,
    ) -> dict:
        """
        Формирует словарь с данными элементов из состава.
        :param one_product_data: Данные ответа нейронки
        :return: словарь
        """
        result_data = {}
        # Оставляем только ключи, начинающиеся с "element_"
        element_only_data = {
            k: v for k, v in one_product_data.items() if k.startswith("element_")
        }
        for index, (element, data) in enumerate(element_only_data.items(), start=1):
            result_data.update(
                self.get_one_element_data(
                    element_name=element, element_index=index, one_element_data=data
                )
            )
        return result_data

    def get_one_element_data(
        self, element_name: str, element_index: int, one_element_data: dict
    ) -> dict:
        """
        Возвращает словарь с информацией об элементе из состава
        :param element_name: имя элемента из ответа ("element_1", "element_777")
        :param element_index: индекс элемента
        :param one_element_data: словарь с информацией по элементу
        :return: {'Aqua (Water)': 'Вода используется как растворител ...', ...}
        """
        element_title = one_element_data.get("Название элемента", "Без названия")
        element_title = element_title[0].upper() + element_title[1:]
        what_is_element_used_for = one_element_data.get(
            "Для чего элемент", "Нет описания"
        )
        what_is_element_used_for = (
            what_is_element_used_for[0].upper() + what_is_element_used_for[1:]
        )
        is_element_danger = one_element_data.get("Опасен элемент или нет", False)
        element_danger_text = one_element_data.get("Чем опасен элемент", "Нет описания")
        danger_level_smile = self.get_danger_level_smile(
            is_element_danger=is_element_danger
        )
        element_danger_text = f"{danger_level_smile} {element_danger_text}"
        element_stop_in_country = one_element_data.get(
            "Элемент запрещён в странах", ""
        ).strip()

        is_not_banned = element_stop_in_country.lower() == "не запрещён."
        ban_text = "" if is_not_banned else element_stop_in_country
        what_is_element_used_for_with_ban = [what_is_element_used_for]
        if ban_text:
            what_is_element_used_for_with_ban.append(ban_text)

        return {
            f"{element_name}_Название элемента": f"{element_index}.  {element_title}",
            f"{element_name}_Для чего элемент": "\n".join(
                what_is_element_used_for_with_ban
            ),
            f"{element_name}_Опасность элемента": element_danger_text,
        }

    def get_conclusion_page_elements(self) -> list:
        """
        Возвращает элементы для отдельной страницы с выводом по средству.
        """
        return [
            ("Spacer", {"width": 1, "height": 30}),
            (
                "Paragraph",
                {"Текст": "<b>Вывод по средству</b>", "Стиль": "ACOP_bold_2"},
            ),
            ("Spacer", {"width": 1, "height": 20}),
            (
                "Paragraph",
                {"Ключ в подборке": "Вывод", "Стиль": "ACOP_normal_3"},
            ),
        ]

    def get_danger_level_smile(
        self,
        is_element_danger: bool,
    ):
        """
        Возвращает смайлик уровня опасности элемента
        """

        danger_smile = {True: "⚠", False: "✅"}

        return danger_smile[is_element_danger]

    def get_composition_elements_data_for_template(
        self,
        one_product_data: dict,
    ) -> list:
        """
        Формирует словарь со стилями и абзацами для вставки в шаблон
        :param one_product_data: данные ответа нейронки
        """
        result_data = []
        for element, _ in one_product_data.items():
            if element.startswith("element_"):
                result_data.extend(
                    self.get_data_template_for_one_element(
                        element_name=element,
                    )
                )
        return result_data

    def get_data_template_for_one_element(
        self,
        element_name: str,
    ) -> list:
        """
        Возвращает список с элементами шаблона и стилями для вставки в документ.

        :param element_name: Имя элемента из ответа ("element_1", "element_777")
        :return: список с элементами шаблона и стилями для вставки в документ
        """

        return [
            (
                "Paragraph",
                {
                    "Ключ в подборке": f"{element_name}_Название элемента",
                    "Стиль": "ACOP_bold_1",
                },
            ),
            ("Spacer", {"width": 1, "height": 13}),
            (
                "Paragraph",
                {
                    "Ключ в подборке": f"{element_name}_Для чего элемент",
                    "Стиль": "ACOP_normal_3",
                },
            ),
            ("Spacer", {"width": 1, "height": -20}),
            (
                "Paragraph",
                {
                    "Ключ в подборке": f"{element_name}_Опасность элемента",
                    "Стиль": "ACOP_normal_3",
                },
            ),
            # ('Paragraph', {
            # 'Ключ в подборке': f'{element_name}_Чем опасен элемент',
            # 'Стиль': 'ACOP_normal_3'},
            # ),
            # ('Paragraph', {
            # 'Ключ в подборке': f'{element_name}_Уровень опасности элемента (числом)',
            # 'Стиль': 'ACOP_bold_1'},
            # ),
            ("Spacer", {"width": 1, "height": 13}),
        ]
