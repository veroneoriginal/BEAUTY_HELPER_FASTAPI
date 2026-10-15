# Тесты beat-страховки run_waiting_task без БД и Redis: ветка QUEUE.
# Сессия, lock, баланс и постановка задачи подменены — проверяем,
# когда страховка перезапускает генерацию подборки в QUEUE.

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from apps.selection.models import SelectionStatus
from infrastructure.celery import tasks


def _run_with_queue_selection(created_ago: int, updated_ago: int) -> MagicMock:
    """
    Одно открытое ожидание с подборкой в QUEUE; возраст — в секундах.
    Возвращает мок run_create_selection_on_task.
    """
    now = datetime.now(timezone.utc)
    selection = SimpleNamespace(
        id=1,
        selection_status=SelectionStatus.QUEUE,
        created_at=now - timedelta(seconds=created_ago),
        updated_at=now - timedelta(seconds=updated_ago),
    )
    session = MagicMock()
    session.execute.return_value.scalars.return_value.all.return_value = [
        SimpleNamespace(selection=selection)
    ]

    @contextmanager
    def fake_session():
        yield session

    @contextmanager
    def free_lock(*args, **kwargs):
        yield True

    create_task = MagicMock()
    with (
        patch.object(tasks, "sync_session", fake_session),
        patch.object(tasks, "redis_lock", free_lock),
        patch.object(tasks, "SyncBalanceService"),
        patch.object(tasks, "_check_stuck_parsing"),
        patch.object(tasks, "run_create_selection_on_task", create_task),
    ):
        tasks.run_waiting_task()
    return create_task


def test_queue_after_long_parsing_is_not_restarted():
    """
    Подборка создана 40 минут назад (шёл парсинг), в QUEUE — 5 секунд:
    генерацию только что поставил парсинг, второй раз не ставим.
    """
    create_task = _run_with_queue_selection(created_ago=40 * 60, updated_ago=5)

    create_task.delay.assert_not_called()


def test_queue_stuck_is_restarted():
    """
    В QUEUE без изменений больше минуты — задача потерялась, перезапускаем.
    """
    create_task = _run_with_queue_selection(created_ago=40 * 60, updated_ago=120)

    create_task.delay.assert_called_once_with(selection_id=1)
