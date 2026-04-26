# apps/package/models.py

# Модели пакетов генераций.
# Package — описание пакета (название, цена, количество генераций).
# UserPackage — факт выдачи пакета пользователю.

import enum
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class UserPackageDelivery(str, enum.Enum):
    """
    Способ получения пакета пользователем.
    """
    PURCHASE = "PURCHASE"   # Покупка
    PROMO = "PROMO"         # Промокод
    MANUAL = "MANUAL"       # Ручное начисление


class Package(Base):
    """
    Пакет генераций.

    Описывает доступный для покупки набор генераций:
    название, количество, цена, активность.

    Защита данных:
    - Удаление запрещено (деактивация через is_active=False).
    - Изменение полей ограничено (только is_active и for_sale).
    Обе проверки — в сервисе.
    """

    __tablename__ = "packages"

    # === Первичный ключ ===
    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="ID пакета",
    )

    # === Основные данные ===
    title: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
        comment="Название пакета",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Описание",
    )
    spins_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Количество генераций в пакете",
    )
    price: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        default=0,
        nullable=False,
        comment="Цена (руб)",
    )

    # === Флаги ===
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Активен ли пакет",
    )
    for_sale: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Доступен ли для продажи",
    )

    def __repr__(self) -> str:
        return f"Package(id={self.id}, title={self.title}, spins={self.spins_count})"


class UserPackage(Base):
    """
    Факт выдачи пакета пользователю.

    Фиксирует: кто получил, какой пакет, каким способом.
    Сам пакет хранит данные (цену, количество) —
    здесь только связь и способ получения.
    """

    __tablename__ = "user_packages"

    # === Первичный ключ ===
    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="ID записи",
    )

    # === Связь с пользователем ===
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="ID пользователя",
    )
    user: Mapped["User"] = relationship(
        "User",
        lazy="joined",
    )

    # === Связь с пакетом ===
    package_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("packages.id", ondelete="SET NULL"),
        nullable=True,
        comment="ID пакета",
    )
    package: Mapped["Package"] = relationship(
        "Package",
        lazy="joined",
    )

    # === Способ получения ===
    delivery_type: Mapped[UserPackageDelivery] = mapped_column(
        Enum(UserPackageDelivery, name="user_package_delivery"),
        default=UserPackageDelivery.PURCHASE,
        nullable=False,
        comment="Способ получения пакета",
    )

    def __repr__(self) -> str:
        return (
            f"UserPackage(id={self.id}, user_id={self.user_id}, "
            f"package_id={self.package_id}, delivery={self.delivery_type})"
        )
