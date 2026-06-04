# core/logging.py
# Единая настройка логирования для приложения и Celery-воркеров.
# Вызывается на старте FastAPI (lifespan) и Celery (сигнал setup_logging),
# чтобы формат и уровень логов были одинаковыми везде.

import logging

from core.config import settings


def configure_logging() -> None:
    """
    Настраивает корневой логгер: формат и уровень.
    Уровень DEBUG при settings.DEBUG, иначе INFO.
    force=True перенастраивает логирование, даже если обработчики уже заданы.
    """
    level = logging.DEBUG if settings.DEBUG else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s | %(message)s",
        force=True,
    )
