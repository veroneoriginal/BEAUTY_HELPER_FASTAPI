#!/bin/bash
set -e

echo "Uploading images to S3..."
python scripts/upload_images_to_s3.py

echo "Importing products into database..."
python scripts/import_products.py

exec uvicorn main:app --host 0.0.0.0 --port 8000
