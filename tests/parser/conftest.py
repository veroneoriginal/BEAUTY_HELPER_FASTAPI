# Общее для тестов парсера: фикстуры — сохранённые ответы API карточки ЗЯ.
# Сеть в тестах не нужна: extractor и normalizer работают с этими JSON.

import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"

# Все сохранённые карточки: имя файла = артикул
ALL_ARTICLES = sorted(path.stem for path in FIXTURES_DIR.glob("*.json"))


def _load_card(article: str) -> dict:
    """
    JSON карточки из fixtures/<артикул>.json.
    """
    path = FIXTURES_DIR / f"{article}.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def load_card():
    """
    Функция «артикул → JSON карточки».
    """
    return _load_card


@pytest.fixture
def make_link():
    """
    Функция «артикул → ссылка на товар», как её присылает пользователь.
    """
    return lambda article: f"https://goldapple.ru/{article}-test"


@pytest.fixture(params=ALL_ARTICLES)
def article(request) -> str:
    """
    Прогоняет тест по всем сохранённым карточкам.
    """
    return request.param
