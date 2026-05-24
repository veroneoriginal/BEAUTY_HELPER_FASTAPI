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


Оркестратор — два движка (sync + async)
FastAPI использует asyncpg,
Celery использует psycopg2.


[1] FastAPI (async HTTP)
Принял запрос, проверил БД, ответил "принято" — быстро

[2] Celery Worker — OpenAI (I/O)
Отправляет запросы к OpenAI
Пока один воркер работает с продуктом А,
другой воркер берёт продукт Б — параллельно

[3] Celery Worker — PDF (CPU)
Когда OpenAI вернул ответ — генерируем PDF
Это отдельный процесс, не блокирует этап 2


task_run_openai(selection_id)
→ OpenAI отработал
→ сохранили ответ в БД
→ вызвали task_generate_pdf.delay(selection_id)

task_generate_pdf(selection_id)
→ взяли данные из БД
→ сгенерировали PDF
→ загрузили на S3
→ закрыли waitings, списали крутки
→ статус DONE