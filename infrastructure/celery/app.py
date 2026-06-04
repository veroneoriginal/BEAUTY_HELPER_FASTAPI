# infrastructure/celery/app.py

from celery import Celery
from celery.signals import setup_logging

from core.config import settings
from core.logging import configure_logging


@setup_logging.connect
def _configure_celery_logging(**kwargs):
    """
    Перехватываем настройку логов Celery и используем общую конфигурацию,
    чтобы формат/уровень совпадали с FastAPI. Подключение к этому сигналу
    отключает собственную настройку логирования Celery.
    """
    configure_logging()


celery_app = Celery(
    "beauty_helper",
    broker=settings.RABBITMQ_URL,
    backend=settings.REDIS_URL,
    include=[
        "infrastructure.celery.tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

celery_app.conf.beat_schedule = {
    "run-waiting-task-every-30-seconds": {
        "task": "infrastructure.celery.tasks.run_waiting_task",
        "schedule": 30.0,
    },
}
