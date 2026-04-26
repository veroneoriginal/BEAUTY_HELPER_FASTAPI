# apps/package/schemas.py

# Pydantic-схемы для модуля package.
# Определяют формат данных на входе и выходе API.

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

# === Пакеты (витрина) ===

class PackageRead(BaseModel):
    """
    Пакет генераций для отображения на витрине.
    """
    id: int
    title: str
    description: str | None = None
    spins_count: int
    price: Decimal

    model_config = {"from_attributes": True}


# === Покупка ===

class BuyPackageRequest(BaseModel):
    """
    Запрос на покупку пакета.
    Пользователь выбирает пакет — генерации начисляются на баланс.
    """
    user_id: int
    package_id: int


class BuyPackageResponse(BaseModel):
    """
    Ответ после покупки пакета.
    """
    message: str


# === История покупок ===

class UserPackageRead(BaseModel):
    """
    Запись о покупке пакета пользователем.
    """
    id: int
    package_id: int | None
    delivery_type: str
    created_at: datetime

    model_config = {"from_attributes": True}


class UserPackageListResponse(BaseModel):
    """
    Список покупок пользователя.
    """
    user_id: int
    packages: list[UserPackageRead]
    