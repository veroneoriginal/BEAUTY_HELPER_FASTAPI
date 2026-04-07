# core/config.py
# Конфигурация приложения.
# Все настройки читаются из .env файла через pydantic-settings.

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Настройки приложения.
    Значения подтягиваются из .env файла автоматически.
    """

    # === Приложение ===
    APP_TITLE: str = "Beauty Helper API"
    DEBUG: bool = True

    # === PostgreSQL ===
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str

    @property
    def database_url(self) -> str:
        """
        Формирует строку подключения к PostgreSQL
        для асинхронного драйвера asyncpg.
        """
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:"
            f"{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:"
            f"{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # === Redis ===
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""

    # === JWT ===
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",  # игнорировать переменные, которых нет в Settings
    }


# Единственный экземпляр настроек на всё приложение
settings = Settings()