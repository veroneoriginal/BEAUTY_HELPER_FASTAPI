# apps/balance/schemas.py

# Pydantic-схемы для модуля balance.
# Определяют формат данных на выходе API.

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

# === Баланс ===

class BalanceRead(BaseModel):
    """
    Текущий баланс пользователя.
    """
    user_id: int
    spins: int
    reserved_spins: int

    model_config = {"from_attributes": True}


# === История операций ===

class OperationRead(BaseModel):
    """
    Одна запись из истории операций.
    """
    id: int
    type_operation: str
    count: int
    description: Optional[str] = None
    balance_after: int
    created_at: datetime

    model_config = {"from_attributes": True}


class OperationListResponse(BaseModel):
    """
    Список операций пользователя.
    """
    user_id: int
    operations: list[OperationRead]
