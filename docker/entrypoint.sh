#!/bin/bash
set -e

# Инициализацию запускаем только для основного сервиса (uvicorn).
# Celery-контейнеры используют тот же образ, им это не нужно.
if [ "${1}" = "uvicorn" ]; then
    echo "Running migrations..."
    alembic upgrade head

    echo "Uploading images to S3..."
    python scripts/upload_images_to_s3.py

    echo "Importing products into database..."
    python scripts/import_products.py
fi

exec "$@"
