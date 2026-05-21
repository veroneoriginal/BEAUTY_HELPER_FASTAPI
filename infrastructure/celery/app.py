# infrastructure/celery/app.py

from celery import Celery

from core.config import settings

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
