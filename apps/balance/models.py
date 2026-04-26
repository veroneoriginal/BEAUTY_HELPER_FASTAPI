# apps/balance/models.py

# Модели, связанные с балансом пользователя.
# UserBalance — текущее количество доступных и зарезервированных генераций.
# BalanceOperation — история всех операций с балансом.

import enum

from sqlalchemy import (
    BigInteger,
    Enum,
    ForeignKey,
    Integer,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class UserBalance(Base):
    """
    Баланс пользователя.

    Отображает текущее количество доступных генераций.
    Обновляется при покупке пакета, активации промокода,
    списании генерации, корректировке админом.
    """

    __tablename__ = "user_balances"

    # === Первичный ключ ===
    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="ID записи баланса",
    )

    # === Связь с пользователем (One-to-One) ===
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        comment="ID пользователя",
    )
    user: Mapped["User"] = relationship("User", lazy="joined", )

    # === Генерации ===
    spins: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Доступные генерации",
    )
    reserved_spins: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Зарезервированные генерации",
    )

    def __repr__(self) -> str:
        return (
            f"UserBalance(user_id={self.user_id}, "
            f"spins={self.spins}, reserved={self.reserved_spins})"
        )


class BalanceOperationType(str, enum.Enum):
    """
    Тип операции с балансом.
    """
    ADD = "ADD"  # Начисление (покупка пакета, промокод)
    RESERVE = "RESERVE"  # Резерв (перед запуском анализа)
    CONFIRM = "CONFIRM"  # Списание (анализ завершён успешно)
    RELEASE = "RELEASE"  # Возврат (анализ завершился ошибкой)
    MANUAL = "MANUAL"  # Ручная корректировка (админ)


class BalanceOperation(Base):
    """
    История операций с балансом пользователя.

    Каждая операция фиксирует: кто, что сделал, сколько,
    и какой баланс стал после операции.
    """

    __tablename__ = "balance_operations"

    # === Первичный ключ ===
    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="ID операции",
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

    # === Данные операции ===
    type_operation: Mapped[BalanceOperationType] = mapped_column(
        Enum(BalanceOperationType, name="balance_operation_type"),
        nullable=False,
        comment="Тип операции",
    )
    count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Количество генераций",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Комментарий к операции",
    )
    balance_after: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Баланс после операции",
    )

    def __repr__(self) -> str:
        return (
            f"BalanceOperation(id={self.id}, user_id={self.user_id}, "
            f"type={self.type_operation}, count={self.count})"
        )
