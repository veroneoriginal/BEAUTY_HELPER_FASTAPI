Тема: Асинхронное веб-приложение с использованием искусственного интеллекта

Суть проекта:
Веб-приложение, которое принимает ссылку на косметическое средство,
анализирует состав через OpenAI API и возвращает PDF-отчёт с детальным разбором каждого компонента.

Фреймворк: FastAPI + Uvicorn
ORM: SQLAlchemy 2.0 (async) + asyncpg
БД: PostgreSQL
Миграции: Alembic
Фоновые задачи: Celery + RabbitMQ
Кэш: Redis
S3: aioboto3 (async версия boto3)
OpenAI: openai SDK (уже поддерживает async)
PDF: ReportLab
Аутентификация: JWT
Контейнеризация: Docker + docker-compose
Тесты: pytest + pytest-asyncio + httpx (AsyncClient)