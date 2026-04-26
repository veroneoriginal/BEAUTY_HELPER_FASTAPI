# apps/package/routes.py

# Эндпоинты для работы с пакетами.
# Витрина пакетов, покупка, история покупок.

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
from core.database import get_session
from core.exceptions import AppError

router = APIRouter(prefix="/packages", tags=["Packages"])


def get_package_service(
        session: AsyncSession = Depends(get_session),
) -> PackageService:
    """
    Dependency для создания PackageService.
    """
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
    description="Пользователь выбирает пакет — "
                "генерации начисляются на баланс.",
)
async def buy_package(
        data: BuyPackageRequest,
        service: PackageService = Depends(get_package_service),
):
    try:
        await service.add_package_to_user(
            user_id=data.user_id,
            package_id=data.package_id,
        )
        return BuyPackageResponse(message="Пакет куплен, генерации начислены")
    except AppError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/{user_id}/history",
    response_model=UserPackageListResponse,
    summary="История покупок",
    description="Возвращает список всех пакетов, "
                "полученных пользователем.",
)
async def get_user_packages(
        user_id: int,
        service: PackageService = Depends(get_package_service),
):
    packages = await service.get_user_packages(user_id)
    return UserPackageListResponse(
        user_id=user_id,
        packages=packages,
    )
