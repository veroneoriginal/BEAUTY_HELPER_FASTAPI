# apps/balance/schemas.py

# Pydantic-схемы для модуля balance.
# Определяют формат данных на входе и выходе API.

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

# === Баланс ===

class BalanceRead(BaseModel):
    """
    Текущий баланс пользователя.
    Отдаём клиенту: сколько доступно, сколько в резерве.
    """
    user_id: int
    spins: int
    reserved_spins: int

    model_config = {"from_attributes": True}


# === Ручное пополнение (для тестирования через Swagger) ===

class AddSpinsRequest(BaseModel):
    """
    Запрос на пополнение баланса.
    Используется для ручного тестирования —
    препод заходит в Swagger и начисляет себе генерации.
    """
    user_id: int
    count: int = Field(gt=0, description="Количество генераций для начисления")


class AddSpinsResponse(BaseModel):
    """
    Ответ после пополнения баланса.
    """
    message: str


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
