# apps/products/models.py


# Модель продукта (косметического средства).
# Содержит все данные, полученные при парсинге карточки товара
# из Золотого Яблока: название, состав, цена, бренд и т.д.

import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    Enum,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class ProductFillStatus(str, enum.Enum):
    """
    Статус заполнения данных продукта.
    Отслеживает, на каком этапе находится парсинг карточки товара.
    """
    EMPTY = "empty"           # Не заполнено
    IN_PROGRESS = "in_progress"  # В процессе
    DONE = "done"             # Заполнено
    FAILED = "failed"         # Ошибка


class Product(Base):
    """
    Модель средства (продукта) Золотого Яблока.

    Данные заполняются парсером: ссылка → парсинг карточки → сохранение.
    После парсинга состав отправляется на анализ через OpenAI API.
    """

    __tablename__ = "products"

    # === Первичный ключ ===
    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="ID продукта",
    )

    # === Ссылка и идентификация ===
    link_ga: Mapped[str] = mapped_column(
        String(2083),
        unique=True,
        nullable=False,
        comment="Уникальная ссылка на карточку товара в Золотом Яблоке",
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Название продукта",
    )
    article_ga: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Артикул в Золотом Яблоке",
    )

    # === Классификация ===
    product_type: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Тип продукта (сокращённо)",
    )
    product_type_detailed: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Тип продукта подробно",
    )
    purpose: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Назначение",
    )
    hair_type: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Тип волос",
    )
    skin_type: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Тип кожи",
    )
    application_area: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Область применения",
    )
    target_audience: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Для кого",
    )

    # === Состав ===
    ingredients: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Состав (полный текст)",
    )
    ingredients_list: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Элементы состава списком",
    )
    ingredients_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Количество элементов состава",
    )

    # === Мера и цена ===
    measure_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Мера (объём или количество)",
    )
    measure_value: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=True,
        comment="Количество меры",
    )
    measure_unit: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Юниты меры (мл или шт)",
    )
    price_rub: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=False,
        comment="Стоимость (руб)",
    )

    # === Описание и применение ===
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Описание",
    )
    usage: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Применение",
    )

    # === Бренд ===
    brand: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Бренд",
    )
    brand_country: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Страна бренда",
    )
    brand_description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Описание бренда",
    )

    # === Дополнительно ===
    additional_info: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Дополнительная информация",
    )
    image_link: Mapped[str | None] = mapped_column(
        String(2083),
        nullable=True,
        comment="Ссылка на изображение в облаке ЗЯ",
    )
    image_key: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Ключ изображения на S3",
    )
    characteristics: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Характеристики",
    )

    # === Статус заполнения ===
    fill_status: Mapped[ProductFillStatus] = mapped_column(
        Enum(ProductFillStatus, name="product_fill_status"),
        default=ProductFillStatus.EMPTY,
        nullable=False,
        comment="Статус заполнения данных",
    )

    # === Временные метки ===
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="Дата создания",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="Дата последнего обновления",
    )

    def __repr__(self) -> str:
        return f"Product(id={self.id}, name={self.name}, article={self.article_ga})"
