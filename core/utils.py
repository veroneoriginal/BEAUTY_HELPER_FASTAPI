# core/utils.py

# Мелкие общие функции, которые нужны нескольким модулям.

from typing import Any


def is_empty(value: Any) -> bool:
    """
    Пустое ли значение: None, пустая строка или пустой список.
    """
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, dict)):
        return not value
    return False
