# apps/package/repository.py

# Репозиторий пакетов.
# Наследует общие CRUD-операции из SQLAlchemyRepository.
# Работает с обеими моделями: Package и UserPackage.

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.package.models import Package, UserPackage
from core.repository.sqlalchemy import SQLAlchemyRepository


class PackageRepository(SQLAlchemyRepository[Package]):
    """
    Репозиторий для работы с пакетами генераций.

    Стандартные методы (get_by_id, get_all, create, update, delete)
    наследуются из SQLAlchemyRepository.

    Здесь — специфичные запросы для Package и UserPackage.
    """

    model = Package

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_active_packages(self) -> list[Package]:
        """
        Получить все активные пакеты, доступные для продажи.
        """
        result = await self.session.execute(
            select(Package).where(
                Package.is_active == True,
                Package.for_sale == True,
                )
        )
        return list(result.scalars().all())

    async def create_user_package(
            self,
            user_id: int,
            package_id: int,
            delivery_type: str,
    ) -> UserPackage:
        """
        Создать запись о выдаче пакета пользователю.
        """
        user_package = UserPackage(
            user_id=user_id,
            package_id=package_id,
            delivery_type=delivery_type,
        )
        self.session.add(user_package)
        await self.session.flush()
        await self.session.refresh(user_package)
        return user_package

    async def get_user_packages(
            self,
            user_id: int,
    ) -> list[UserPackage]:
        """
        Получить все пакеты пользователя.
        Сортировка — от новых к старым.
        """
        result = await self.session.execute(
            select(UserPackage)
            .where(UserPackage.user_id == user_id)
            .order_by(UserPackage.created_at.desc())
        )
        return list(result.scalars().all())
