# apps/selection/services.py

# Сервисный слой модуля selection.
# Содержит бизнес-логику: создание подборки, смена статуса,
# привязка пользователя, сохранение результатов OpenAI.
# Сервис работает ТОЛЬКО через репозиторий — не знает про SQLAlchemy напрямую.

from typing import Sequence

from apps.selection.models import Selection, SelectionStatus, SelectionTaskType
from apps.selection.repository import SelectionRepository
from apps.users.models import User


class SelectionService:
    """
    Бизнес-логика для работы с подборками.

    Принимает репозиторий как зависимость.
    Не знает ни про SQLAlchemy, ни про сессии —
    только про интерфейс репозитория.
    """

    def __init__(self, repository: SelectionRepository):
        self.repository = repository

    # === Создание ===

    async def create_selection(
            self,
            product_id: int,
            task_type: SelectionTaskType,
    ) -> Selection:
        """
        Создаёт подборку в статусе QUEUE.
        """
        selection = await self.repository.create({
            "product_id": product_id,
            "task_type": task_type,
            "selection_status": SelectionStatus.QUEUE,
        })
        await self.repository.session.commit()
        return selection

    # === Получение ===

    async def get_selection_by_id(
            self,
            selection_id: int,
    ) -> Selection | None:
        """Получить подборку по ID."""
        return await self.repository.get_by_id(selection_id)

    async def get_by_product_and_task_type(
            self,
            link_ga: str,
            task_type: str | SelectionTaskType,
    ) -> Selection | None:
        """
        Найти подборку по ссылке на продукт и типу задачи.
        """
        return await self.repository.get_by_product_and_task_type(
            link_ga=link_ga,
            task_type=task_type,
        )

    async def get_all_selections(self) -> Sequence[Selection]:
        """ Получить все подборки."""
        return await self.repository.get_all()

    # === Проверка готовности для пользователя ===

    async def get_ready_selection_for_user(
            self,
            selection: Selection | None,
            user_id: int,
    ) -> str | None:
        """
        Проверяет, есть ли у пользователя готовая подборка,
        и можно ли её сразу отдать.

        Возвращает сообщение если подборка готова, None если нет.
        """
        if not selection:
            return None

        if (
                selection.selection_status == SelectionStatus.DONE
                and await self.repository.has_user(selection.id, user_id)
        ):
            return "Эта подборка у Вас уже есть. Отправляем PDF."

        return None

    # === Привязка пользователя ===

    async def add_user_to_selection(
            self,
            selection: Selection,
            user: User,
    ) -> None:
        """
        Привязать пользователя к подборке.
        Если пользователь уже привязан — ничего не делает.
        """
        await self.repository.add_user(selection, user)
        await self.repository.session.commit()

    # === Смена статуса ===

    async def mark_as_processing(
            self,
            selection_id: int,
    ) -> Selection | None:
        """
        Перевести подборку в статус PROCESS.
        Вызывается когда воркер берёт задачу в работу.
        """
        selection = await self.repository.update(
            selection_id,
            {"selection_status": SelectionStatus.PROCESS},
        )
        await self.repository.session.commit()
        return selection

    async def finish(
            self,
            selection_id: int,
            pdf_url: str,
    ) -> Selection | None:
        """
        Завершить подборку: записать ссылку на PDF,
        перевести статус подборки в DONE.
        """
        selection = await self.repository.update(
            selection_id,
            {
                "pdf_url": pdf_url,
                "selection_status": SelectionStatus.DONE,
            },
        )
        await self.repository.session.commit()
        return selection

    async def mark_as_failed(
            self,
            selection_id: int,
            error_message: str,
    ) -> Selection | None:
        """
        Пометить подборку как неудавшуюся.
        Сохраняет сообщение об ошибке для диагностики.
        """
        selection = await self.repository.update(
            selection_id,
            {
                "selection_status": SelectionStatus.FAILED,
                "error_message": error_message,
            },
        )
        await self.repository.session.commit()
        return selection

    # === Сохранение данных OpenAI ===

    async def set_request_details(
            self,
            selection_id: int,
            json_str: str,
    ) -> Selection | None:
        """
        Сохранить данные, отправленные в OpenAI.
        """
        selection = await self.repository.update(
            selection_id,
            {"request_details": json_str},
        )
        await self.repository.session.commit()
        return selection

    async def set_final_analysis(
            self,
            selection_id: int,
            json_str: str,
    ) -> Selection | None:
        """
        Принимает ответы от OPENAI в виде JSON-строки и
        сохраняет в финальный ответ от OpenAI.
        """
        selection = await self.repository.update(
            selection_id,
            {"final_analysis": json_str},
        )
        await self.repository.session.commit()
        return selection

    async def calculate_price(
            self,
            selection_id: int,
            price_request: dict,
    ) -> Selection | None:
        """
        Сохранить информацию о стоимости запроса к OpenAI.
        """
        selection = await self.repository.update(
            selection_id,
            {"price": price_request},
        )
        await self.repository.session.commit()
        return selection

    # === Удаление ===

    async def delete_selection(
            self,
            selection_id: int,
    ) -> bool:
        """Удалить подборку."""
        result = await self.repository.delete(selection_id)
        await self.repository.session.commit()
        return result
