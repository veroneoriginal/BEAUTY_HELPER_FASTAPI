# apps/pdf_generation/creator_logic/creator/fonts_and_styles/styles.py

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import (
    TTFont,
)

from apps.pdf_generation.creator_logic.creator.fonts_and_styles.analysis_composition_one_product import (
    ANALYSIS_COMPOSITION_ONE_PRODUCT_STYLES,
)
from apps.pdf_generation.creator_logic.creator.fonts_and_styles.best_product import (
    BEST_PRODUCT_STYLES,
)
from core.assets import FONTS_DIR

FONTS_NAME = [
    "DejaVuSans",
    "DejaVuSans-Bold",
    "Montserrat-Medium",
    "Montserrat-Bold",
    "Montserrat-Regular",
    "Montserrat-SemiBold",
    "Symbola",
]

FONTS = tuple((fontname, f"{FONTS_DIR}/{fontname}.ttf") for fontname in FONTS_NAME)

for font in FONTS:
    pdfmetrics.registerFont(TTFont(name=font[0], filename=font[1]))

PDF_STYLE = {}
PDF_ADDITIONAL_STYLES = (
    BEST_PRODUCT_STYLES,
    ANALYSIS_COMPOSITION_ONE_PRODUCT_STYLES,
)
for style in PDF_ADDITIONAL_STYLES:
    PDF_STYLE.update(style)
