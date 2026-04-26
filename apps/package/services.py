# apps/package/services.py

# Сервисный слой модуля package.
# Содержит бизнес-логику: создание пакетов, выдача пользователю,
# защита от изменения и удаления.
# При выдаче пакета — начисляет генерации через BalanceService.

from apps.balance.repository import BalanceRepository
from apps.balance.services import BalanceService
from apps.package.models import Package, UserPackage, UserPackageDelivery
from apps.package.repository import PackageRepository
from core.exceptions import AppError, PackageProtectedError


class PackageService:
    """
    Бизнес-логика для работы с пакетами генераций.

    Принимает репозиторий как зависимость.
    Защита данных:
    - Удаление пакета запрещено (деактивация через is_active=False).
    - Изменение полей ограничено (только is_active и for_sale).
    """

    # Поля, которые разрешено менять после создания пакета
    ALLOWED_UPDATE_FIELDS = {"is_active", "for_sale"}

    def __init__(self, repository: PackageRepository):
        self.repository = repository

    # === Создание ===

    async def create_package(
            self,
            data: dict,
    ) -> Package:
        """
        Создать новый пакет генераций.
        После создания поля (title, price, spins_count) заморожены —
        менять можно только is_active и for_sale.
        """
        package = await self.repository.create(data)
        await self.repository.session.commit()
        return package

    # === Чтение ===

    async def get_package_by_id(
            self,
            package_id: int,
    ) -> Package | None:
        """Получить пакет по ID."""
        return await self.repository.get_by_id(package_id)

    async def get_active_packages(self) -> list[Package]:
        """Получить все активные пакеты, доступные для продажи."""
        return await self.repository.get_active_packages()

    async def get_all_packages(self) -> list[Package]:
        """Получить все пакеты (для админки)."""
        result = await self.repository.get_all()
        return list(result)

    # === Обновление (с защитой) ===

    async def update_package(
            self,
            package_id: int,
            data: dict,
    ) -> Package | None:
        """
        Обновить пакет.

        Разрешено менять только is_active и for_sale.
        Попытка изменить другие поля — PackageProtectedError.
        """
        forbidden = set(data.keys()) - self.ALLOWED_UPDATE_FIELDS
        if forbidden:
            raise PackageProtectedError(
                f"Поля {', '.join(forbidden)} нельзя изменять. "
                f"Разрешены только: {', '.join(self.ALLOWED_UPDATE_FIELDS)}."
            )

        package = await self.repository.update(package_id, data)
        await self.repository.session.commit()
        return package

    # === Удаление (запрещено) ===

    async def delete_package(
            self,
            package_id: int,
    ) -> None:
        """
        Удаление пакета запрещено.
        """
        raise PackageProtectedError(
            "Удаление пакета запрещено. Используйте is_active=False."
        )

    # === Выдача пакета пользователю ===

    async def add_package_to_user(
            self,
            user_id: int,
            package_id: int,
            delivery_type: str = UserPackageDelivery.PURCHASE,
    ) -> UserPackage:
        """
        Выдать пакет пользователю.

        1. Проверяет, что пакет существует и активен.
        2. Создаёт запись UserPackage.
        3. Начисляет генерации на баланс через BalanceService.
        4. Один commit на всё — если что-то упадёт, откатится всё.

        Аналог функции add_package_to_user из Django
        (apps/package/services/add_package_to_user.py).
        """
        # Проверяем пакет
        package = await self.repository.get_by_id(package_id)
        if package is None:
            raise AppError("Пакет не найден")

        if not package.is_active:
            raise AppError("Пакет неактивен")

        # Создаём запись о выдаче
        user_package = await self.repository.create_user_package(
            user_id=user_id,
            package_id=package_id,
            delivery_type=delivery_type,
        )

        # Начисляем генерации на баланс
        # Используем ту же сессию — одна транзакция
        balance_service = BalanceService(
            BalanceRepository(self.repository.session)
        )
        await balance_service.add_spins_no_commit(
            user_id=user_id,
            count=package.spins_count,
            description=f"Начисление за пакет «{package.title}»",
        )

        await self.repository.session.commit()
        return user_package

    # === История пакетов пользователя ===

    async def get_user_packages(
            self,
            user_id: int,
    ) -> list[UserPackage]:
        """Получить все пакеты пользователя."""
        return await self.repository.get_user_packages(user_id)
