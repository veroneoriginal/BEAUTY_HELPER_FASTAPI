# apps/pdf_generation/creator_logic/creator/custom_flowables.py

from reportlab.lib.colors import Color, HexColor
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Flowable


class FreeText(Flowable):
    """
    Абсолютно позиционированный текст, рисуется вне фрейма.
    Координаты (x, y) — от верхнего левого угла страницы (как и в других Free*).
    """

    def __init__(
        self,
        text: str,
        x: float,
        y: float,
        font_name: str = "DejaVuSans",
        font_size: float = 10,
        font_color: str = "#FFFFFFDD",
        bold: bool = False,
        align: str = "left",  # left, center, right
    ):
        super().__init__()
        self.absolute = 1
        self.text = text
        self.x = x
        self.y = y
        self.font_name = font_name + ("-Bold" if bold else "")
        self.font_size = font_size
        self.font_color = HexColor(
            val=font_color,
            hasAlpha=True,
        )
        self.align = align.lower()
        self._fixedHeight = 0
        self._fixedWidth = 0

    def wrap(self, availWidth, availHeight):
        return (0, 0)

    def draw(self):
        c = self.canv
        c.saveState()

        c.setFont(self.font_name, self.font_size)
        c.setFillColor(self.font_color)

        text_width = c.stringWidth(self.text, self.font_name, self.font_size)

        if self.align == "center":
            draw_x = self.x - text_width / 2
        elif self.align == "right":
            draw_x = self.x - text_width
        else:  # left
            draw_x = self.x

        # Внимание: координаты в ReportLab начинаются от низа страницы
        c.drawString(draw_x, self.y, self.text)

        c.restoreState()


class FreeRect(Flowable):
    """
    Прямоугольник с абсолютным позиционированием, рисуется вне фрейма.
    Координаты (x, y) — от верхнего левого угла страницы.
    """

    def __init__(
        self,
        x: int | float,
        y: int | float,
        width: int | float,
        height: int | float,
        fill_color: str | Color = HexColor("#F2F2F2"),
        stroke_color: str | Color = None,
        stroke_width: int | float = 0,
        radius: float = 0,
    ):
        super().__init__()
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.fill_color = HexColor(fill_color)
        self.stroke_color = HexColor(stroke_color) if stroke_color else None
        self.stroke_width = stroke_width
        self.radius = radius
        self._fixedHeight = 0
        self._fixedWidth = 0

    def wrap(self, availWidth, availHeight):
        return (0, 0)

    def draw(self):
        c = self.canv
        c.saveState()

        # Цвет заливки
        c.setFillColor(self.fill_color)

        # Обводка
        if self.stroke_color:
            c.setStrokeColor(self.stroke_color)
            c.setLineWidth(self.stroke_width)
        else:
            c.setLineWidth(0)

        # Прямоугольник с радиусом (скругление)
        if self.radius > 0:
            c.roundRect(
                self.x, self.y, self.width, self.height, self.radius, stroke=1, fill=1
            )
        else:
            c.rect(
                self.x,
                self.y,
                self.width,
                self.height,
                stroke=1 if self.stroke_color else 0,
                fill=1,
            )

        c.restoreState()


class FreeImage(Flowable):
    """
    Кастомное flowables-изображение, для рисования
    изображения вне фрейма с абсолютным позиционированием.
    Координаты 0, 0 в верхнем левом углу фрейма
    """

    def __init__(
        self,
        path: str,
        x: int | float,
        y: int | float,
        width: int | float | None = None,
        height: int | float | None = None,
        preserve_aspect_ratio: bool = False,
    ):
        super().__init__()
        self.path = path
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.preserve_aspect_ratio = preserve_aspect_ratio
        self._fixedHeight = 0  # чтобы он не занимал места в потоке
        self._fixedWidth = 0

    def wrap(self, availWidth: float | int, availHeight: float | int):
        """Возвращаем 0, чтобы он не влиял на layout"""
        return (0, 0)

    def check_image_size(self) -> tuple:
        """Автоматическое определение размеров изображения"""
        img = ImageReader(self.path)
        img_width, img_height = img.getSize()

        draw_width = self.width
        draw_height = self.height
        if draw_width is None and draw_height is None:
            draw_width = img_width
            draw_height = img_height
        elif draw_width is None:
            draw_width = img_width * (self.height / img_height)
        elif draw_height is None:
            draw_height = img_height * (self.width / img_width)

        return draw_width, draw_height

    def draw(self):

        draw_width, draw_height = self.check_image_size()

        self.canv.drawImage(
            self.path,
            self.x,
            self.y,
            width=draw_width,
            height=draw_height,
            mask="auto",
            preserveAspectRatio=self.preserve_aspect_ratio,
        )
