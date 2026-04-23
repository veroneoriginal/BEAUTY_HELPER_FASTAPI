# core/database.py
# Асинхронное подключение к PostgreSQL через SQLAlchemy 2.0.

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

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


class Base(DeclarativeBase):
    """
    Базовый класс для всех моделей.
    Аналог BaseModel из Django-проекта.
    """
    pass


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency для FastAPI.
    Создаёт сессию на время запроса и закрывает после.
    """
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
