# apps/users/models.py

# Модель пользователя.
# Основной идентификатор для входа — email + пароль.
# telegram_id — опциональная привязка Telegram-аккаунта.

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class User(Base):
    """
    Модель пользователя.

    Регистрация через сайт (email + пароль).
    Telegram-аккаунт можно привязать позже.
    """

    __tablename__ = "users"

    # === Первичный ключ ===
    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="Внутренний ID пользователя",
    )

    # === Авторизация ===
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        comment="Email — основной идентификатор для входа",
    )
    password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Хеш пароля",
    )

    # === Профиль ===
    username: Mapped[str | None] = mapped_column(
        String(150),
        unique=True,
        nullable=True,
        comment="Отображаемое имя (опционально)",
    )
    # === Telegram (опциональная привязка) ===
    telegram_id: Mapped[int | None] = mapped_column(
        BigInteger,
        unique=True,
        nullable=True,
        comment="ID пользователя в Telegram (привязка позже)",
    )
    language_code: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
        comment="Код языка (ru, en и т.д.)",
    )

    # === Флаги ===
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="Активен ли аккаунт",
    )
    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Суперпользователь",
    )
    is_banned: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Заблокирован ли пользователь",
    )
    email_confirmed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Подтверждён ли email",
    )

    # === Временные метки ===
    last_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Последний вход",
    )
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
        return f"User(id={self.id}, email={self.email})"
