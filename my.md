

Тема: Разработка асинхронного веб-приложения с использованием искусственного интеллекта.

Суть проекта: Веб-приложение, которое принимает ссылку на косметическое средство, анализирует состав через OpenAI API и возвращает PDF-отчёт с детальным разбором каждого компонента.
Стек: Python, asyncio,FastAPI, PostgreSQL, Redis, RabbitMQ, Celery, Docker, S3, OpenAI API, ReportLab.

Какие компетенции покрываются:
Устройство языка — asyncio, async/await, httpx/aiohttp, asyncpg, декораторы, dataclasses (DTO), работа с OpenAI SDK, ReportLab, boto3.
Web-программирование — REST API, асинхронные views, проектирование эндпоинтов, сериализация, обработка статусов подборки.
High performance — async I/O вместо блокирующих вызовов (OpenAI API, S3, парсинг), профилирование и бенчмарки sync vs async, Celery для фоновых задач.
Анализ данных — визуализация бенчмарков (графики latency, throughput), анализ стоимости запросов к OpenAI.
Software engineering — чистая модульная архитектура (selectors/services/models), Docker + docker-compose, PostgreSQL, Redis, RabbitMQ, S3, тесты (unit + integration), паттерны Service Layer.

План работы:
Проектирование архитектуры асинхронного приложения
Реализация async REST API
Асинхронное взаимодействие с OpenAI API, S3, базой данных
Система баланса, пакетов и промокодов
Генерация PDF-отчётов
Фоновые задачи (Celery)
Профилирование и бенчмарки
Тесты и документация