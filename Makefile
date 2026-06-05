# Проверяет весь код в текущей папке
lint:
	ruff check .

# Отформатировать код
format:
	ruff format .

# Автоматически исправляет то, что может.
# Например, удалит неиспользуемый импорт или отсортирует импорты по алфавиту.
lint_fix:
	ruff check --fix .

test: ## Прогнать тесты (локально, в .venv)
	python -m pytest -q

test-v: ## Прогнать тесты подробно (имя каждого теста)
	python -m pytest -v

check: ## Проверка перед пушем: линт + формат + тесты (как в CI)
	ruff check .
	ruff format --check .
	python -m pytest -q

up: ## Запустить всё в Docker
	docker compose -f docker/docker-compose.yaml --env-file .env up -d --build

down: ## Остановить и удалить контейнеры + тома
	docker compose -f docker/docker-compose.yaml --env-file .env down -v

logs: ## Хвост логов всех сервисов
	docker compose -f docker/docker-compose.yaml --env-file .env logs -f --tail=200

rebuild: ## Полная пересборка образов и перезапуск
	docker compose -f docker/docker-compose.yaml --env-file .env up -d --build --force-recreate

migrate: ## Сгенерировать миграцию (нужна запущенная БД: make up-db)
	POSTGRES_HOST=localhost alembic revision --autogenerate -m "$(m)"

up-db: ## Запустить только PostgreSQL
	docker compose -f docker/docker-compose.yaml --env-file .env up -d db

shell: ## Войти внутрь контейнера backend
	docker exec -it bh_backend bash

restart-worker: ## Перезапустить Celery worker после изменений кода
	docker restart bh_celery
