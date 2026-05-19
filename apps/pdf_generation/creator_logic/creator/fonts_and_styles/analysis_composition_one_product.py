# apps/pdf_generation/creator_logic/creator/fonts_and_styles/analysis_composition_one_product.py

from reportlab.lib.enums import (
    TA_CENTER,
    TA_JUSTIFY,
    TA_LEFT,
)
from reportlab.lib.styles import (
    ParagraphStyle,
)

ANALYSIS_COMPOSITION_ONE_PRODUCT_STYLES = {
    'ACOP_title_1': ParagraphStyle(
        'ACOP_title_1',
        fontName="Montserrat-Bold",
        fontSize=25,
        leading=35,
        alignment=TA_CENTER,
    ),
    'ACOP_title_2': ParagraphStyle(
        'ACOP_title_2',
        fontName="Montserrat-Bold",
        fontSize=25,
        alignment=TA_CENTER,
    ),
    'ACOP_base_price_1': ParagraphStyle(
        'ACOP_base_price_1',
        fontName="Montserrat-Regular",
        fontSize=20,
        alignment=TA_CENTER,
    ),

    'ACOP_price_ratio_1': ParagraphStyle(
        'ACOP_price_ratio_1',
        fontName="Montserrat-Regular",
        fontSize=20,
        alignment=TA_CENTER,
    ),

    'ACOP_normal_2': ParagraphStyle(
        'ACOP_normal_2',
        fontName="Montserrat-Regular",
        alignment=TA_CENTER,
        fontSize=20,
        leading=20,
    ),
    'ACOP_normal_3': ParagraphStyle(
        'ACOP_normal_3',
        fontName="Montserrat-Regular",
        alignment=TA_JUSTIFY,
        fontSize=15,
        leading=20,
        spaceAfter=20,

    ),
    'ACOP_bold_1': ParagraphStyle(
        'ACOP_bold_1',
        fontName="Montserrat-Bold",
        fontSize=21,
        alignment=TA_LEFT,
        leading=25,
    ),
    'ACOP_bold_2': ParagraphStyle(
        'ACOP_bold_2',
        fontName="Montserrat-Bold",
        fontSize=21,
        alignment=TA_CENTER,
        leading=25,
    ),
}
