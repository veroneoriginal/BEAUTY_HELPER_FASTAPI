# apps/balance/routes.py

# Эндпоинты для работы с балансом.
# Просмотр баланса, ручное пополнение (для тестирования),
# просмотр истории операций.

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.balance.repository import BalanceRepository
from apps.balance.schemas import (
    AddSpinsRequest,
    AddSpinsResponse,
    BalanceRead,
    OperationListResponse,
)
from apps.balance.services import BalanceService
from core.database import get_session

router = APIRouter(prefix="/balance", tags=["Balance"])


def get_balance_service(
        session: AsyncSession = Depends(get_session),
) -> BalanceService:
    """
    Dependency для создания BalanceService.
    """
    repository = BalanceRepository(session)
    return BalanceService(repository)


# Depends(get_balance_service) делает всё автоматически:
# создаёт сессию → создаёт репозиторий → создаёт сервис
# → передаёт в эндпоинт. После ответа сессия закрывается.

@router.get(
    "/{user_id}",
    response_model=BalanceRead,
    summary="Просмотр баланса",
    description="Возвращает текущий баланс пользователя: "
                "доступные и зарезервированные генерации.",
)
async def get_balance(
        user_id: int,
        service: BalanceService = Depends(get_balance_service),
):
    balance = await service.get_balance(user_id)
    if balance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Баланс не найден",
        )
    return balance


@router.post(
    "/add",
    response_model=AddSpinsResponse,
    summary="Пополнение баланса",
    description="Ручное начисление генераций. "
                "Используется для тестирования через Swagger.",
)
async def add_spins(
        data: AddSpinsRequest,
        service: BalanceService = Depends(get_balance_service),
):
    result = await service.add_spins(
        user_id=data.user_id,
        count=data.count,
        description="Ручное пополнение через Swagger",
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Баланс не найден. Сначала зарегистрируйтесь.",
        )
    return AddSpinsResponse(
        message=f"Начислено {data.count} генераций",
    )


@router.get(
    "/{user_id}/operations",
    response_model=OperationListResponse,
    summary="История операций",
    description="Возвращает список всех операций с балансом пользователя. "
                "Сортировка — от новых к старым.",
)
async def get_operations(
        user_id: int,
        service: BalanceService = Depends(get_balance_service),
):
    operations = await service.get_operations(user_id)
    return OperationListResponse(
        user_id=user_id,
        operations=operations,
    )