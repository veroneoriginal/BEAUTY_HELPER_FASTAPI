# apps/orchestrator/router.py

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from apps.orchestrator.service import get_or_prepare_selection
from apps.selection.models import SelectionTaskType
from apps.selection.repository import SelectionRepository
from apps.selection.services import SelectionService
from apps.users.models import User
from core.database import get_session
from core.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/selection", tags=["Selection"])


class AnalysisRequest(BaseModel):
    """
    Схема запроса на анализ косметического продукта.
    """

    product_link: str
    task_type: SelectionTaskType = SelectionTaskType.COMPOSITION_ANALYSIS


class AnalysisResponse(BaseModel):
    """
    Схема ответа на запрос анализа.
    """

    status: str
    message: str
    pdf_url: str | None = None


class SelectionItem(BaseModel):
    """
    Подборка в списке «Мои анализы».
    """

    id: int
    product_name: str | None = None
    product_link: str | None = None
    status: str
    pdf_url: str | None = None

    model_config = {"from_attributes": True}


@router.post(
    "/",
    response_model=AnalysisResponse,
    summary="Анализ косметического средства",
    description="Принимает ссылку на продукт, запускает анализ состава"
                " через OpenAI и возвращает ссылку на PDF-отчёт.",
)
async def analyze_product(
    request: AnalysisRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AnalysisResponse:
    """
    Главный эндпоинт для анализа продукта.

    Флоу:
    1. Проверяет есть ли готовая подборка → отдаёт PDF
    2. Подборка в процессе → добавляет в ожидание
    3. Подборки нет → создаёт, запускает Celery-задачу

    :param request: ссылка на продукт и тип задачи
    :param current_user: авторизованный пользователь (из JWT)
    :param session: async сессия БД
    :return: статус и сообщение для пользователя
    """
    logger.info(
        "[ROUTER] User %s requested analysis for %s",
        current_user.id,
        request.product_link,
    )

    result = await get_or_prepare_selection(
        user=current_user,
        product_link=request.product_link,
        task_type=request.task_type,
        session=session,
    )

    return AnalysisResponse(**result)


@router.get(
    "/my",
    response_model=list[SelectionItem],
    summary="Мои подборки",
    description="Возвращает список всех подборок авторизованного пользователя.",
)
async def get_my_selections(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[SelectionItem]:
    """
    Возвращает все подборки авторизованного пользователя.

    Каждая подборка содержит название и ссылку на продукт,
    текущий статус (QUEUE, PROCESS, DONE, FAILED) и ссылку на PDF
    если анализ завершён.

    :param current_user: авторизованный пользователь (из JWT)
    :param session: async сессия БД
    :return: список подборок пользователя, от новых к старым
    """
    service = SelectionService(SelectionRepository(session))
    selections = await service.get_user_selections(user_id=current_user.id)

    return [
        SelectionItem(
            id=s.id,
            product_name=s.product.name if s.product else None,
            product_link=s.product.link_ga if s.product else None,
            status=s.selection_status,
            pdf_url=s.pdf_url,
        )
        for s in selections
    ]
