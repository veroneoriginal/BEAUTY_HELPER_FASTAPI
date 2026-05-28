# apps/package/routes.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.package.repository import PackageRepository
from apps.package.schemas import (
    BuyPackageRequest,
    BuyPackageResponse,
    PackageRead,
    UserPackageListResponse,
)
from apps.package.services import PackageService
from apps.users.models import User
from core.database import get_session
from core.exceptions import AppError
from core.security import get_current_user

router = APIRouter(prefix="/packages", tags=["Packages"])


def get_package_service(
    session: AsyncSession = Depends(get_session),
) -> PackageService:
    repository = PackageRepository(session)
    return PackageService(repository)


@router.get(
    "/",
    response_model=list[PackageRead],
    summary="Витрина пакетов",
    description="Возвращает список активных пакетов, доступных для покупки.",
)
async def get_packages(
    service: PackageService = Depends(get_package_service),
):
    return await service.get_active_packages()


@router.post(
    "/buy",
    response_model=BuyPackageResponse,
    summary="Покупка пакета",
    description="Пользователь выбирает пакет — генерации начисляются на баланс.",
)
async def buy_package(
    data: BuyPackageRequest,
    current_user: User = Depends(get_current_user),
    service: PackageService = Depends(get_package_service),
):
    try:
        await service.add_package_to_user(
            user_id=current_user.id,
            package_id=data.package_id,
        )
        return BuyPackageResponse(message="Пакет куплен, генерации начислены")
    except AppError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/me/history",
    response_model=UserPackageListResponse,
    summary="История покупок",
    description="Возвращает список всех пакетов, полученных авторизованным пользователем.",
)
async def get_user_packages(
    current_user: User = Depends(get_current_user),
    service: PackageService = Depends(get_package_service),
):
    packages = await service.get_user_packages(current_user.id)
    return UserPackageListResponse(
        user_id=current_user.id,
        packages=packages,
    )
