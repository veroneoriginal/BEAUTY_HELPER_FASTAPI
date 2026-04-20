# api/auth.py

# Эндпоинты для регистрации, подтверждения email, логина и обновления токенов.
# Роуты: принимают запрос, вызывают сервис, возвращают ответ.

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.auth.schemas import (
    ConfirmEmailResponse,
    LoginRequest,
    LogoutRequest,
    LogoutResponse,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
)
from apps.auth.services import AuthService
from apps.users.repository import UserRepository
from core.database import get_session

router = APIRouter(prefix="/auth", tags=["Auth"])


def get_auth_service(
        session: AsyncSession = Depends(get_session),
) -> AuthService:
    """
    Dependency для создания AuthService.
    FastAPI автоматически подставляет сессию из get_session,
    создаёт репозиторий и передаёт в сервис.
    """
    repository = UserRepository(session)
    return AuthService(repository)


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация нового пользователя",
    description="Создаёт аккаунт (email + пароль). "
                "На почту отправляется ссылка для подтверждения email.",
)
async def register(
        data: RegisterRequest,
        service: AuthService = Depends(get_auth_service),
):
    try:
        result = await service.register(data=data)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/confirm/{token}",
    response_model=ConfirmEmailResponse,
    summary="Подтверждение email",
    description="Пользователь переходит по ссылке из письма. "
                "Токен из URL проверяется, email подтверждается.",
)
async def confirm_email(
        token: str,
        service: AuthService = Depends(get_auth_service),
):
    try:
        result = await service.confirm_email(token)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Вход в аккаунт",
    description="Email + пароль → пара токенов (access + refresh). "
                "Email должен быть подтверждён.",
)
async def login(
        data: LoginRequest,
        service: AuthService = Depends(get_auth_service),
):
    try:
        result = await service.login(data)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Обновление токенов",
    description="Отправляем refresh_token → получаем новую пару "
                "(access + refresh). Используется когда access_token протух.",
)
async def refresh(
        data: RefreshRequest,
        service: AuthService = Depends(get_auth_service),
):
    try:
        result = await service.refresh_tokens(data.refresh_token)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


@router.post(
    "/logout",
    response_model=LogoutResponse,
    summary="Выход из аккаунта",
    description="Инвалидирует access и refresh токены. "
                "После logout токены перестают работать.",
)
async def logout(
        data: LogoutRequest,
        service: AuthService = Depends(get_auth_service),
):
    result = await service.logout(data.access_token, data.refresh_token)
    return result
