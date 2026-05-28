# apps/pdf_generation/creator_logic/creator/document_creator.py

from io import BytesIO
from pathlib import Path
from typing import Tuple

from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    FrameBreak,
    Image,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
)

from apps.pdf_generation.creator_logic.creator.custom_flowables import (
    FreeImage,
    FreeRect,
    FreeText,
)
from apps.pdf_generation.creator_logic.creator.fonts_and_styles.styles import PDF_STYLE
from apps.pdf_generation.utils import replace_emoji_html


def _pixels_to_points(
    pixels: int | float,
) -> int | float:
    """
    Конвертирование пикселей в поинты.

    В типографике поинты (pt) используются как единицы измерения.
    В reportlab и PDF стандартный DPI (dots per inch) = 72 dpi.
    В экранах и изображениях стандартный DPI = 96 dpi.
    Поэтому, чтобы перевести из 96 dpi → 72 dpi,
    используется коэффициент 72 / 96 = 0.75.

    :param pixels: Значение изображения в пикселях
    :return: значение изображения в поинтах
    """

    return pixels * 72 / 96


class PDFPageTemplateandFrameBuilder:
    """
    Создаёт фреймы и шаблоны страниц для PDF-документа
    """

    def _create_frame(
        self,
        x1_y1: Tuple[float, float],
        width_height: Tuple[float, float],
        frame_id: str,
    ) -> Frame:
        """
        Создает и добавляет в список объект Frame, который определяет
        область на странице. На этой странице будут размещаться элементы (flowables)
        внутри BaseDocTemplate.

        x1 и y1 - координаты нижнего левого угла фрейма
        width и height - ширина и высота фрейма

        :param x1_y1: кортеж с координатами нижнего угла для фрейма
        :param width_height: кортеж с шириной и высотой фрейма
        :param frame_id: идентификатор (имя) фрейма

        :return: None
        """

        return Frame(
            x1=_pixels_to_points(x1_y1[0]),
            y1=_pixels_to_points(x1_y1[1]),
            width=_pixels_to_points(width_height[0]),
            height=_pixels_to_points(width_height[1]),
            id=frame_id,
            # showBoundary=True,
        )

    def _create_frames(
        self,
        frames_data: tuple,
    ) -> list[Frame]:
        """
        Создаёт фреймы для шаблона страниц
        :param frames_data: кортеж с кортежами фреймов с данными
        :return: список фреймов
        """
        frames = []
        for frame in frames_data:
            created_frame = self._create_frame(
                frame_id=str(frame[0]),
                x1_y1=frame[1],
                width_height=frame[2],
            )
            frames.append(created_frame)
        return frames

    def _create_page_template(
        self,
        frames: list[Frame],
        template_id: str,
    ) -> PageTemplate:
        """
        Создание шаблона страницы.

        :param frames: Список объектов Frame, определяющих области для размещения элементов.
        :param template_id: Идентификатор (имя) шаблона страницы
        :return: шаблон страницы, который будет использоваться в PDF
        """

        return PageTemplate(
            id=template_id,
            frames=frames,
        )

    def create_doc_templates(self, templates_data: dict) -> list[PageTemplate]:
        """
        Создаёт шаблоны страниц с фреймами.

        :param templates_data: Словарь с данными по шаблонам страниц и фреймам
        :return: список готовых шаблонов страниц
        """
        templates = []

        for template_id, frames_data in templates_data.items():
            frames = self._create_frames(frames_data=frames_data)
            template = self._create_page_template(
                frames=frames, template_id=template_id
            )
            templates.append(template)

        return templates


class PDFBaseDocTemplateWithBrandLine(BaseDocTemplate):
    """
    Создаёт шаблон документа с переопределением
    метода afterPage для нанесения бренд линии
    на каждую страницу документа
    """

    # pylint: disable=W0012 unknown-option-value
    # pylint: disable=R0917 too-many-positional-argument
    # pylint: disable=R0913 too-many-arguments
    def __init__(
        self,
        filename: str,
        doc_width_height: tuple,
        brand_line_width_height: tuple,
        path_to_brandline_file: Path,
        brand_line_coords: list[tuple[int, int], ...],
        **kwargs,
    ):
        """
        :param filename: имя PDF-документа
        :param doc_width_height: ширина и высота документа
        :param brand_line_width_height:  ширина и высота бренд-линии
        :param path_to_brandline_file: путь к файлу с бренд-линией
        :param brand_line_coords: координаты вставки бренд-линии (x, y)
        """
        self.doc_width_height = doc_width_height
        self.brand_line_width_height = brand_line_width_height
        self.path_to_brandline_file = path_to_brandline_file
        self.brand_line_coords = brand_line_coords

        super().__init__(
            filename=filename,
            pagesize=(
                _pixels_to_points(self.doc_width_height[0]),
                _pixels_to_points(self.doc_width_height[1]),
            ),
            **kwargs,
        )

    # pylint: disable=W0613: unused-argument
    def _add_brandline(
        self,
        canvas: Canvas,
        doc: BaseDocTemplate,
    ):
        """
        Рисует бренд-линию на канве
        """

        for coords in self.brand_line_coords:
            canvas.drawImage(
                image=self.path_to_brandline_file,
                x=_pixels_to_points(coords[0]),  # x (левый край)
                y=_pixels_to_points(coords[1]),  # y (нижний край)
                width=_pixels_to_points(pixels=self.brand_line_width_height[0]),
                height=_pixels_to_points(pixels=self.brand_line_width_height[1]),
            )

    def afterPage(self):
        """
        Вызывается каждый раз после обработки каждой страницы
        """

        self._add_brandline(self.canv, self)


class PDFFlowablesCreator:
    """
    Создание flowables-элементы для PDF-документа: абзацы, картинки и т.д.
    """

    def __init__(
        self,
        data: dict,
        image_in_bytes: bytes,
    ):
        self.data = data
        self.flowables: list[Flowable] = []
        self.image_in_bytes = image_in_bytes

    def create_flowables(self) -> list[Flowable]:
        """
        Создаёт flowables-элементы для PDF-документа: абзацы, картинки и т.д.

        :return: Список flowables-элементов.
        """
        flowables_structure = self.data["Элементы и стили"]
        for flowable_object in flowables_structure:
            flowable_type = flowable_object[0]
            flowable_data = flowable_object[1]
            match flowable_type:
                case "Image":
                    self._create_image(
                        img_bytes=self.image_in_bytes,
                        width=_pixels_to_points(flowable_data["width"]),
                        height=_pixels_to_points(flowable_data["height"]),
                    )
                case "Paragraph":
                    text = (
                        flowable_data.get("Текст", None)
                        or self.data[flowable_data["Ключ в подборке"]]
                    )
                    self._create_paragraph(
                        text=text,
                        style=self._get_style(flowable_data["Стиль"]),
                        upper=flowable_data.get("Заглавными", False),
                    )
                case "Spacer":
                    self._create_spacer(
                        width=_pixels_to_points(flowable_data["width"]),
                        height=_pixels_to_points(flowable_data["height"]),
                    )
                case "NextPageTemplate":
                    self.flowables.append(
                        NextPageTemplate(pt=flowable_data["template_id"])
                    )
                case "PageBreak":
                    self.flowables.append(PageBreak())
                case "FrameBreak":
                    self.flowables.append(FrameBreak())
                case "FreeImage":
                    self.flowables.append(
                        FreeImage(
                            path=self.data[flowable_data.get("Ключ в подборке")],
                            x=_pixels_to_points(flowable_data.get("x")),
                            y=_pixels_to_points(flowable_data.get("y")),
                            width=_pixels_to_points(flowable_data.get("width")),
                            height=_pixels_to_points(flowable_data.get("height")),
                            preserve_aspect_ratio=flowable_data.get(
                                "preserve_aspect_ratio"
                            ),
                        )
                    )
                case "FreeRect":
                    self.flowables.append(
                        FreeRect(
                            x=_pixels_to_points(flowable_data.get("x")),
                            y=_pixels_to_points(flowable_data.get("y")),
                            width=_pixels_to_points(flowable_data.get("width")),
                            height=_pixels_to_points(flowable_data.get("height")),
                            fill_color=flowable_data.get("fill_color"),
                        )
                    )
                case "FreeText":
                    text = (
                        flowable_data.get("Текст", None)
                        or self.data[flowable_data["Ключ в подборке"]]
                    )
                    self.flowables.append(
                        FreeText(
                            text=text,
                            x=_pixels_to_points(flowable_data.get("x")),
                            y=_pixels_to_points(flowable_data.get("y")),
                            font_name=flowable_data.get("font_name"),
                            font_size=flowable_data.get("font_size"),
                            font_color=flowable_data.get("font_color"),
                            bold=flowable_data.get("bold"),
                            align=flowable_data.get("align"),
                        )
                    )

        return self.flowables

    def _create_paragraph(
        self,
        text: str,
        style: ParagraphStyle,
        upper: bool,
    ) -> None:
        """
        Создаёт параграф с текстом и добавляет в общий список
        :param text: текст
        :param style: стиль
        :param upper: сделать заглавными
        :return: None
        """

        text_with_smile = replace_emoji_html(text)

        paragraph = Paragraph(
            text=text_with_smile.upper() if upper else text_with_smile,
            style=style,
        )
        self.flowables.append(paragraph)

    def _get_style(
        self,
        style_name,
    ):
        """
        Возвращает объект стиля по имени
        """
        return PDF_STYLE[style_name]

    def _create_image(self, img_bytes: bytes, width: int, height: int) -> None:
        """
        Создаёт изображение и добавляет в общий список
        :param img_bytes: изображение в байтах
        :param width: ширина изображения
        :param height: высота изображения
        :return: None
        """
        img_stream = BytesIO(img_bytes)
        img = Image(img_stream, width=width, height=height, kind="proportional")
        self.flowables.append(img)

    def _create_spacer(self, width: int, height: int) -> None:
        """
        Создаёт spacer и добавляет в общий список
        :param width: ширина spacer
        :param height: высота spacer
        :return: None
        """
        spacer = Spacer(width, height)
        self.flowables.append(spacer)


TEMPLATE_CLASS = {
    "PDFBaseDocTemplateWithBrandLine": PDFBaseDocTemplateWithBrandLine,
}
