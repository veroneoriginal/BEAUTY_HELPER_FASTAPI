# main.py
# Точка входа в приложение.

from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.auth import router as auth_router

# Импортируем модели, чтобы SQLAlchemy увидел их при create_all.
# Без этого Base.metadata будет пустой и таблицы не создадутся.
from apps.users.models import User  # noqa: F401
from core.database import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    При старте — создаёт таблицы в БД (если их нет).
    При остановке — закрывает пул соединений.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="Beauty Helper API",
    description="Асинхронное API для анализа состава косметических средств",
    version="0.1.0",
    lifespan=lifespan,
)

# === Роутеры регистрации и аутентификации ===
app.include_router(auth_router)


@app.get("/health")
async def health_check():
    """
    Проверка, что сервер работает.
    """
    return {"status": "ok"}
