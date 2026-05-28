# apps/balance/routes.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.balance.repository import BalanceRepository
from apps.balance.schemas import BalanceRead, OperationListResponse
from apps.balance.services import BalanceService
from apps.users.models import User
from core.database import get_session
from core.security import get_current_user

router = APIRouter(prefix="/balance", tags=["Balance"])


def get_balance_service(
    session: AsyncSession = Depends(get_session),
) -> BalanceService:
    repository = BalanceRepository(session)
    return BalanceService(repository)


@router.get(
    "/me",
    response_model=BalanceRead,
    summary="Просмотр баланса",
    description="Возвращает текущий баланс авторизованного пользователя.",
)
async def get_balance(
    current_user: User = Depends(get_current_user),
    service: BalanceService = Depends(get_balance_service),
):
    balance = await service.get_balance(current_user.id)
    if balance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Баланс не найден",
        )
    return balance


@router.get(
    "/me/operations",
    response_model=OperationListResponse,
    summary="История операций",
    description="Возвращает список всех операций с балансом авторизованного пользователя.",
)
async def get_operations(
    current_user: User = Depends(get_current_user),
    service: BalanceService = Depends(get_balance_service),
):
    operations = await service.get_operations(current_user.id)
    return OperationListResponse(
        user_id=current_user.id,
        operations=operations,
    )
