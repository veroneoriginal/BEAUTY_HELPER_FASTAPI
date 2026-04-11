# Проверяет весь код в текущей папке
lint:
	ruff check .

# Автоматически исправляет то, что может.
# Например, удалит неиспользуемый импорт или отсортирует импорты по алфавиту.
lint_fix:
	ruff check . --fix

up: ## Запустить всё в Docker
	docker network inspect bh_network >/dev/null 2>&1 || docker network create bh_network
	docker compose -f docker/docker-compose.yaml --env-file .env up -d --build

down: ## Остановить и удалить контейнеры + тома
	docker compose -f docker/docker-compose.yaml --env-file .env down -v

logs: ## Хвост логов всех сервисов
	docker compose -f docker/docker-compose.yaml --env-file .env logs -f --tail=200

rebuild: ## Полная пересборка образов и перезапуск
	docker compose -f docker/docker-compose.yaml --env-file .env up -d --build --force-recreate

shell: ## Войти внутрь контейнера backend
	docker exec -it bh_backend bash
