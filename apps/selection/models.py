# apps/selection/models.py

# Модель подборки (Selection).
# Подборка — результат анализа состава продукта через OpenAI API.
# Содержит: ссылку на продукт, тип задачи, статус, PDF, ответ от OpenAI.
# Связь с пользователями — Many-to-Many через промежуточную таблицу.

import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Table,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base

# === Промежуточная таблица для связи Selection ↔ User ===
# В Django это ManyToManyField, в SQLAlchemy — явная Table.
# Хранит пары (selection_id, user_id).

selection_users = Table(
    "selection_users",
    Base.metadata,
    Column(
        "selection_id",
        BigInteger,
        ForeignKey("selections.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "user_id",
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


# === Enum-классы ===
# Классы, в которых заранее определены все допустимые значения.

class SelectionStatus(str, enum.Enum):
    """
    Статус генерации подборки.
    Отслеживает, на каком этапе находится процесс создания.
    """
    QUEUE = "queue"              # Задача поставлена, воркер ещё не взял
    PROCESS = "process"          # Подборка создаётся (запросы, PDF)
    ON_REVIEW = "on_review"      # PDF готов, модератор не проверил
    DONE = "done"                # Прошла модерацию, можно отправлять
    DEVIATION = "deviation"      # Отклонена модератором
    FAILED = "failed"            # Ошибка создания


class SelectionTaskType(str, enum.Enum):
    """
    Тип задачи, по которой создаётся подборка.
    """
    COMPOSITION_ANALYSIS = "detailed_analysis"  # Подробный анализ состава
    BEST_CHOICE = "best"                        # Лучшее средство
    ANALOG = "analog"                           # Аналог


# === Модель ===

class Selection(Base):
    """
    Модель подборки.

    Подборка привязана к одному продукту (ForeignKey)
    и может быть доступна нескольким пользователям (ManyToMany).

    Жизненный цикл:
    QUEUE → PROCESS → ON_REVIEW → DONE / DEVIATION
                   ↘ FAILED (при ошибке)
    """

    __tablename__ = "selections"

    # === Первичный ключ ===
    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="ID подборки",
    )

    # === Связь с продуктом (Many-to-One) ===
    product_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        comment="ID продукта, по которому сделана подборка",
    )
    product: Mapped["Product"] = relationship(
        "Product",
        lazy="joined",
    )

    # === Связь с пользователями (Many-to-Many) ===
    users: Mapped[list["User"]] = relationship(
        "User",
        secondary=selection_users,
        lazy="selectin",
    )

    # === Тип задачи ===
    task_type: Mapped[str] = mapped_column(
        Enum(SelectionTaskType, name="selection_task_type"),
        nullable=False,
        comment="Тип задачи подборки",
    )

    # === Статус ===
    selection_status: Mapped[str] = mapped_column(
        Enum(SelectionStatus, name="selection_status"),
        default=SelectionStatus.QUEUE,
        nullable=False,
        comment="Статус генерации подборки",
    )

    # === PDF ===
    pdf_url: Mapped[str | None] = mapped_column(
        String(2083),
        nullable=True,
        comment="Ссылка на PDF-файл подборки",
    )

    # === Данные OpenAI ===
    request_details: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Отправленные данные в OpenAI для анализа",
    )
    final_analysis: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Финальный ответ от OpenAI",
    )

    # === Стоимость ===
    price: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Стоимость запроса к OpenAI",
    )

    # === Ошибки ===
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Сообщение об ошибке",
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
        return (
            f"Selection(id={self.id}, product_id={self.product_id}, "
            f"task_type={self.task_type}, status={self.selection_status})"
        )
