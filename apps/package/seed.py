# apps/package/seed.py

# Предзаполнение пакетов генераций.
# Запускается один раз при первом развёртывании.
# Создаёт пакеты, если их ещё нет в базе.

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.package.models import Package


async def seed_packages(session: AsyncSession) -> None:
    """
    Создаёт стандартные пакеты, если таблица пустая.
    """
    result = await session.execute(select(Package))
    if result.scalars().first() is not None:
        return  # пакеты уже есть

    packages = [
        Package(
            title="Базовый",
            description="3 генерации",
            spins_count=3,
            price=199.00,
            is_active=True,
            for_sale=True,
        ),
        Package(
            title="Стандартный",
            description="10 генераций",
            spins_count=10,
            price=499.00,
            is_active=True,
            for_sale=True,
        ),
        Package(
            title="Премиум",
            description="30 генераций",
            spins_count=30,
            price=1199.00,
            is_active=True,
            for_sale=True,
        ),
    ]

    session.add_all(packages)
    await session.commit()
