# DTO (Data Transfer Object) для продукта.
# Используется для передачи данных о продукте вне контекста ORM.
# Нужен для анализа состава, формирования подборок и других операций,
# где требуется только информация о продукте без привязки к БД.

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class ProductData:
    """
    DTO продукта.

    frozen=True — объект неизменяемый после создания.
    slots=True — оптимизация памяти, запрещает динамические атрибуты.
    """
    name: str                              # Название продукта
    article_ga: str                        # Артикул в Золотом Яблоке
    image_key: str | None                  # Ключ изображения на S3
    product_type: str | None               # Тип продукта (сокращённо)
    product_type_detailed: str | None      # Детализированный тип продукта
    measure_value: Decimal | None          # Количество меры (объём, штуки и т.д.)
    measure_unit: str | None               # Единица измерения (мл, шт и т.д.)
    price_rub: Decimal | None              # Цена в рублях
    ingredients_list: list[str] | None     # Список ингредиентов
