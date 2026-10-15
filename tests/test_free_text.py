# Тесты FreeText: привязка текста к краю картинки над ним.
# Canvas ReportLab подменён: проверяем только, где рисуется строка.

from unittest.mock import MagicMock

from apps.pdf_generation.creator_logic.creator.custom_flowables import FreeText

FRAME_WIDTH = 900  # ширина фрейма; картинка стоит по его центру
TEXT_WIDTH = 100  # ширина строки, которую «вернёт» stringWidth


def _draw_x(align: str, x: float, image_width: float, offset: float = 10) -> float:
    """
    Рисует FreeText на подменённом canvas и возвращает x, где начата строка.
    """
    text = FreeText(
        text="артикул: 1",
        x=x,
        y=0,
        font_name="Helvetica",
        align=align,
        image_width=image_width,
        image_offset=offset,
    )
    text.wrap(FRAME_WIDTH, 0)
    text.canv = MagicMock()
    text.canv.stringWidth.return_value = TEXT_WIDTH
    text.draw()
    return text.canv.drawString.call_args.args[0]


def test_right_align_sticks_to_narrow_image_right_edge():
    """
    Узкая картинка 300 по центру фрейма 900: правый край 600.
    Текст справа заканчивается на 600 − 10, а не на заданном x.
    """
    assert _draw_x("right", x=800, image_width=300) == 590 - TEXT_WIDTH


def test_right_align_wide_image_stays_on_x():
    """
    Картинка во весь фрейм: правее заданного x текст не уходит.
    """
    assert _draw_x("right", x=800, image_width=900) == 800 - TEXT_WIDTH


def test_left_align_sticks_to_narrow_image_left_edge():
    """
    Левая привязка (подпись правообладателя) работает как раньше.
    """
    assert _draw_x("left", x=-40, image_width=300) == 300 + 10
