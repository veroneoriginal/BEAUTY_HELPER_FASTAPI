# apps/waiting/models.py

import enum

from sqlalchemy import BigInteger, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class WaitingStatus(str, enum.Enum):
    """
    Статусы модели Ожидание.
    """
    OPEN = "open"      # Ожидание открыто
    CLOSED = "closed"  # Ожидание завершено


class Waiting(Base):
    """
    Модель ожидания отправки подборки пользователю.
    Создаётся на каждый запрос пользователя на генерацию подборки.

    Жизненный цикл: OPEN → CLOSED
    """

    __tablename__ = "waitings"

    # Один пользователь — одно ожидание на одну подборку.
    # Это ограничение на уровне БД, не на уровне кода.
    __table_args__ = (
        UniqueConstraint("user_id", "selection_id", name="uq_waiting_user_selection"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="ID ожидания",
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="Пользователь который ожидает подборку",
    )
    user: Mapped["User"] = relationship("User", lazy="joined")

    selection_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("selections.id", ondelete="CASCADE"),
        nullable=False,
        comment="Подборка за которой следим",
    )
    selection: Mapped["Selection"] = relationship("Selection", lazy="joined")

    status: Mapped[str] = mapped_column(
        Enum(WaitingStatus, name="waiting_status"),
        default=WaitingStatus.OPEN,
        nullable=False,
        comment="Текущий статус ожидания",
    )

    def __repr__(self) -> str:
        return (
            f"Waiting(id={self.id}, user_id={self.user_id}, "
            f"selection_id={self.selection_id}, status={self.status})"
        )