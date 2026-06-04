# core/database.py
# Асинхронное подключение к PostgreSQL через SQLAlchemy 2.0.

from collections.abc import AsyncGenerator
from datetime import datetime

from sqlalchemy import DateTime, create_engine, func
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from core.config import settings

# Движок — управляет пулом соединений к PostgreSQL
engine = create_async_engine(
    url=settings.database_url,
    echo=settings.DEBUG,  # логирование SQL-запросов в консоль
)

# Фабрика сессий — каждый запрос получает свою сессию
async_session = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# === Синхронный движок (для Celery-воркеров) ===
sync_engine = create_engine(
    url=settings.database_url.replace(
        "postgresql+asyncpg",
        "postgresql+psycopg2",
    ),
    echo=settings.DEBUG,
)

sync_session = sessionmaker(
    bind=sync_engine,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """
    Базовый класс для всех моделей.
    Аналог BaseModel из Django-проекта.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="Дата создания",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="Дата последнего обновления",
    )


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Async dependency для FastAPI.

    Dependency для FastAPI — это функция которую FastAPI автоматически
    вызывает перед каждым эндпоинтом и передаёт результат как аргумент.

    Создаёт сессию на время запроса и закрывает после.
    """
    async with async_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
