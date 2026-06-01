# Beauty Helper API

Асинхронное веб-приложение с использованием ИИ.

Пользователь вставляет ссылку на косметическое средство → приложение анализирует
состав через OpenAI API → возвращает PDF-отчёт с детальным разбором каждого компонента.

**Только бэкенд. Демо через Swagger (`/docs`).**

---

## Стек

| Слой | Технология |
|---|---|
| Фреймворк | FastAPI + Uvicorn |
| ORM | SQLAlchemy 2.0 (async через asyncpg, sync через psycopg2) |
| БД | PostgreSQL |
| Миграции | Alembic |
| Фоновые задачи | Celery + RabbitMQ (брокер) + Celery Beat (периодика) |
| Кэш / счётчики / локи | Redis |
| Хранилище файлов | S3 (aioboto3) |
| ИИ | OpenAI SDK, модель `gpt-4o-mini`, structured output через tool_calls |
| PDF | ReportLab |
| Аутентификация | JWT (PyJWT) + bcrypt |
| Контейнеризация | Docker + docker-compose |
| Линт/формат | Ruff |

---

## Архитектура

Ключевое решение — **граница sync / async** проходит между HTTP-слоем и воркером:

- **FastAPI** работает асинхронно через `asyncpg`.
- **Celery** работает синхронно через `psycopg2`.

Это разные движки и сессии (`core/database.py`) и разные реализации репозиториев
(`core/repository/sqlalchemy.py` — async, `sync_sqlalchemy.py` — sync), чтобы не
смешивать event loop с блокирующими вызовами.

```
[1] FastAPI (async, asyncpg)
    router → orchestrator/service → service → repository (AsyncSession)
    Принимает запрос, проверяет БД, резервирует "крутку",
    ставит задачу в Celery и быстро отвечает статусом
    (created / pending / done / parsing / error).

        │ run_create_selection_on_task.delay(selection_id)
        ▼

[2] Celery Worker (sync, psycopg2)
    Одна задача делает весь пайплайн генерации подборки:
      1. OpenAI — состав делится на шаги по 10 ингредиентов,
         каждый шаг идёт отдельным запросом (KeyManager + Limiter)
      2. Расчёт стоимости запроса (токены → USD/RUB)
      3. PDF — ReportLab → bytes
      4. Загрузка PDF на S3
      5. Закрытие ожиданий (Waiting), списание/возврат круток
      6. Статус подборки → DONE / FAILED
    Идемпотентность: Redis-lock на selection_id, retry (max 3), acks_late.

[3] Celery Beat (каждые 30 сек: run_waiting_task)
    Страховка: дозакрывает зависшие ожидания и перезапускает
    подборки, застрявшие в QUEUE.
```

> Примечание: весь пайплайн (OpenAI → PDF → S3) выполняет **одна** Celery-задача
> `run_create_selection_on_task`, а не цепочка отдельных задач. PDF-этап грузит файл
> на S3 через `asyncio.run(...)` внутри синхронного воркера.

### Система баланса («крутки»)

За одну генерацию списывается одна «крутка». Модель резерва защищает от потери
круток при ошибках и гонках:

```
spins (доступные)  --reserve-->  reserved_spins (в работе)
                                       │
                          успех  ──────┼──── confirm  (reserved -1)
                          ошибка ──────┴──── release  (reserved -1, spins +1)
```

Все операции блокируют строку баланса (`SELECT FOR UPDATE`) и пишут историю
в таблицу `balance_operations` (`ADD / RESERVE / CONFIRM / RELEASE / MANUAL`).

---

## Флоу пользователя

1. **Регистрация** → возвращается токен подтверждения email.
2. **Подтверждение email** по токену.
3. **Логин** → пара токенов (access + refresh).
4. **Покупка пакета** → крутки начисляются на баланс (оплата — заглушка).
5. **Отправка ссылки на средство** (`POST /selection/`). Оркестратор выбирает ветку:
   - подборка уже **готова (DONE)** → резерв + списание крутки → отдаём `pdf_url`;
   - подборка **в процессе (QUEUE/PROCESS)** → резерв крутки → добавляем в ожидание;
   - подборки нет, но **продукт есть в БД** → резерв → создаём подборку → Celery-задача;
   - **продукта нет в БД** → заглушка парсера (статус `parsing`).
6. **Получение результата** — когда задача завершится, статус станет `done`,
   а `GET /selection/my` отдаст ссылку на PDF.

---

## API-эндпоинты

| Метод | Путь | Назначение | Auth |
|---|---|---|---|
| POST | `/auth/register` | Регистрация (возвращает токен подтверждения) | — |
| GET | `/auth/confirm/{token}` | Подтверждение email | — |
| POST | `/auth/login` | Логин → access + refresh | — |
| POST | `/auth/refresh` | Обновление пары токенов | — |
| POST | `/auth/logout` | Выход (blacklist токенов в Redis) | — |
| GET | `/packages/` | Витрина пакетов | — |
| POST | `/packages/buy` | Покупка пакета (начисление круток) | ✅ |
| GET | `/packages/me/history` | История покупок | ✅ |
| GET | `/balance/me` | Текущий баланс | ✅ |
| GET | `/balance/me/operations` | История операций баланса | ✅ |
| POST | `/selection/` | Анализ средства по ссылке | ✅ |
| GET | `/selection/my` | Список своих подборок | ✅ |
| GET | `/health` | Healthcheck | — |

Авторизация: заголовок `Authorization: Bearer <access_token>`. В Swagger — кнопка **Authorize**.

Полный интерактивный список — Swagger UI: `http://localhost:8000/docs`.

---

## Запуск

### 1. Переменные окружения

Создайте `.env` в корне проекта (полный список переменных — в `core/config.py`):

```env
# Приложение
DEBUG=false

# PostgreSQL
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=db            # имя сервиса в docker-compose
POSTGRES_PORT=5432
POSTGRES_DB=beauty_helper

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=redis_pass

# RabbitMQ
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672//

# JWT
SECRET_KEY=change-me
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# OpenAI (два аккаунта для ротации ключей)
OPENAI_API_KEY_ACCOUNT_ONE=sk-...
OPENAI_API_KEY_ACCOUNT_TWO=sk-...

# S3
S3_ENDPOINT_URL=https://...
S3_ACCESS_KEY_ID=...
S3_SECRET_KEY=...
S3_BUCKET_NAME=...
```

### 2. Поднять всё в Docker

```bash
make up        # сборка и запуск: db, redis, rabbitmq, app, celery worker, celery beat
make logs      # хвост логов
make down      # остановить и удалить контейнеры + тома
```

При первом старте `app` (см. `docker/entrypoint.sh`):
прогоняются миграции Alembic, демо-картинки загружаются на S3,
демо-продукты импортируются в БД.

После запуска:
- Swagger: `http://localhost:8000/docs`
- RabbitMQ Management: `http://localhost:15672`

> После изменений кода Celery нужно перезапустить: `make restart-worker`.

### Полезные команды

```bash
make migrate m="описание"   # создать миграцию (нужна запущенная БД: make up-db)
make lint                   # ruff check .
make format                 # ruff format .
make shell                  # bash внутри контейнера app
```

---

## Демо-сценарий

Готовые ссылки на средства и пример прохождения флоу через Swagger —
в `tests/swagger.md`.

---

## Текущие ограничения

- **Парсер** карточек товара — заглушка (`apps/parsers/`). Анализируются только
  продукты, заранее импортированные в БД.
- **Оплата** — заглушка: покупка пакета сразу начисляет крутки.
- **Промокоды** — заглушка (на будущее).
- **Email** не отправляется: токен подтверждения возвращается прямо в ответе регистрации.
- Из типов задач реализован только подробный анализ состава (`detailed_analysis`).