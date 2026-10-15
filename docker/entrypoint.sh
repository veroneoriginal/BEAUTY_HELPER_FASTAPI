#!/bin/bash
set -e

# Инициализацию запускаем только для основного сервиса (uvicorn).
# Celery-контейнеры используют тот же образ, им это не нужно.
if [ "${1}" = "uvicorn" ]; then
    echo "Running migrations..."
    alembic upgrade head
fi

exec "$@"
