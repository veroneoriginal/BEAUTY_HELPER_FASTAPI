# Общая настройка тестов.
# Импортируем все модели, чтобы они зарегистрировались в mapper registry
# (как это делает main.py). Иначе relationship по строковым именам, например
# UserBalance.user -> "User", не резолвятся и инициализация маппера падает.

import os

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

import apps.balance.models  # noqa: F401
import apps.package.models  # noqa: F401
import apps.products.models  # noqa: F401
import apps.selection.models  # noqa: F401
import apps.users.models  # noqa: F401
import apps.waiting.models  # noqa: F401
from core.config import settings
from core.database import Base

# === Интеграционные тесты на реальной БД ===
TEST_DB_NAME = os.getenv("TEST_POSTGRES_DB", "beauty_helper_test")
TEST_DB_HOST = os.getenv("TEST_POSTGRES_HOST", "localhost")


def _build_url(driver: str, db_name: str) -> str:
    """
    Строит DSN тестовой БД из settings, но с тестовым хостом и именем БД.
    """
    return (
        f"postgresql+{driver}://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{TEST_DB_HOST}:{settings.POSTGRES_PORT}/{db_name}"
    )


@pytest.fixture(scope="session")
def _test_db():
    """
    Готовит тестовую БД на сессию: создаёт beauty_helper_test, если её нет,
    и накатывает схему через create_all. Если Postgres недоступен — пропускает
    все интеграционные тесты (а не падает), чтобы юнит-тесты и простой CI
    оставались зелёными.
    """
    admin_url = _build_url("psycopg2", "postgres")
    try:
        admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
        with admin_engine.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": TEST_DB_NAME},
            ).scalar()
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{TEST_DB_NAME}"'))
        admin_engine.dispose()
    except OperationalError as exc:
        pytest.skip(f"Postgres недоступен — интеграционные тесты пропущены: {exc}")

    engine = create_engine(_build_url("psycopg2", TEST_DB_NAME))
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
async def db_session(_test_db):
    """
    Async-сессия на тестовой БД. Каждый тест идёт в SAVEPOINT с откатом:
    commit() внутри сервисов оркестратора не доходит до реальной БД, поэтому
    данные между тестами не копятся и тесты не зависят друг от друга.
    """
    engine = create_async_engine(_build_url("asyncpg", TEST_DB_NAME))
    conn = await engine.connect()
    trans = await conn.begin()
    session = AsyncSession(bind=conn, expire_on_commit=False)
    await session.begin_nested()

    @event.listens_for(session.sync_session, "after_transaction_end")
    def _restart_savepoint(sess, transaction):
        # как только сервис делает commit (release savepoint) — открываем новый
        if transaction.nested and not transaction._parent.nested:
            sess.begin_nested()

    try:
        yield session
    finally:
        await session.close()
        await trans.rollback()
        await conn.close()
        await engine.dispose()
