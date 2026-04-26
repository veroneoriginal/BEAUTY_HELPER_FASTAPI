# main.py
# Точка входа в приложение.

from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.auth import router as auth_router

# Импортируем модели, чтобы SQLAlchemy увидел их при create_all.
# Без этого Base.metadata будет пустой и таблицы не создадутся.
from apps.balance.models import BalanceOperation, UserBalance  # noqa: F401
from apps.balance.routes import router as balance_router
from apps.package.models import Package, UserPackage  # noqa: F401
from apps.package.routes import router as package_router
from apps.package.seed import seed_packages
from apps.products.models import Product  # noqa: F401
from apps.selection.models import Selection, selection_users  # noqa: F401
from apps.users.models import User  # noqa: F401
from core.database import Base, async_session, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    При старте — создаёт таблицы в БД (если их нет).
    При остановке — закрывает пул соединений.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Предзаполнение пакетов (один раз при первом запуске)
    async with async_session() as session:
        await seed_packages(session)

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
app.include_router(balance_router)
app.include_router(package_router)


@app.get("/health")
async def health_check():
    """
    Проверка, что сервер работает.
    """
    return {"status": "ok"}
