# core/assets.py

from pathlib import Path

# Корень проекта
BASE_DIR = Path(__file__).resolve().parent.parent

ASSETS_DIR = BASE_DIR / "assets"

ORANGE_LIGHT_VERTICAL_BRAND_LINE_PATH = (
    ASSETS_DIR / "imagine_border" / "border_orange_light.jpg"
)

FONTS_DIR = ASSETS_DIR / "fonts"
EMOJI_IMAGE_DIR = ASSETS_DIR / "emoji"
