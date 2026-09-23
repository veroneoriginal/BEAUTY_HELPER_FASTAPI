# apps/parser/dto.py

# DTO результата парсинга карточки товара.
# Это граница модуля парсера: парсер отдаёт ParsedProduct
# и ничего не знает ни про БД, ни про другие модули apps/.
# Какие поля критичные — решает apps/products, а не парсер.
# Поля совпадают с полями модели Product.

from dataclasses import dataclass, fields
from decimal import Decimal
from typing import Any

from core.utils import is_empty


@dataclass(slots=True)
class ParsedProduct:
    """
    Данные товара, собранные парсером.

    Все поля, кроме link_ga, опциональные:
    None — поле не нашли на сайте.
    """

    # === Ссылка и идентификация ===
    link_ga: str  # Ссылка на карточку товара в Золотом Яблоке
    name: str | None = None  # Название (бренд + название)
    article_ga: str | None = None  # Артикул в Золотом Яблоке

    # === Классификация ===
    product_type: str | None = None  # Тип продукта (сокращённо)
    product_type_detailed: str | None = None  # Тип продукта подробно
    purpose: str | None = None  # Назначение
    hair_type: str | None = None  # Тип волос
    skin_type: str | None = None  # Тип кожи
    application_area: str | None = None  # Область применения
    target_audience: str | None = None  # Для кого

    # === Состав ===
    ingredients: str | None = None  # Состав (полный текст)
    ingredients_list: list[str] | None = None  # Элементы состава списком
    ingredients_count: int | None = None  # Количество элементов состава

    # === Мера и цена ===
    measure_type: str | None = None  # Мера (объём или количество)
    measure_value: Decimal | None = None  # Количество меры
    measure_unit: str | None = None  # Юниты меры (мл или шт)
    price_rub: Decimal | None = None  # Стоимость (руб)

    # === Описание и применение ===
    description: str | None = None  # Описание
    usage: str | None = None  # Применение

    # === Бренд ===
    brand: str | None = None  # Бренд
    brand_country: str | None = None  # Страна бренда
    brand_description: str | None = None  # Описание бренда

    # === Дополнительно ===
    additional_info: str | None = None  # Дополнительная информация
    image_link: str | None = None  # Ссылка на изображение в облаке ЗЯ
    image_key: str | None = None  # Ключ изображения на S3 (ставится после загрузки)
    characteristics: str | None = None  # Характеристики (JSON-строка)

    def to_dict(self) -> dict[str, Any]:
        """
        Только заполненные поля — для update_product.

        Пустые не отдаём, чтобы не затереть данные,
        которые админ внёс руками.
        """
        return {
            f.name: getattr(self, f.name)
            for f in fields(self)
            if not is_empty(getattr(self, f.name))
        }
