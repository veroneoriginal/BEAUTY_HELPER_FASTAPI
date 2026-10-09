# apps/parser/tools/try_media.py

# Ручная проверка картинки (шаг 7): media.ImageUploader на живом CDN и настоящем S3.
# На сайт ЗЯ не ходим: ссылку на картинку берём из фикстуры (extract + normalize).
# Хранилище — настоящий S3Service из infrastructure, ключи из .env.
#
# Запуск — из корня проекта (команды есть в commands.md):
#   python -m apps.parser.tools.try_media                        — Erborian 9400200001, напрямую
#   python -m apps.parser.tools.try_media --article 19000002015  — другая фикстура
#   python -m apps.parser.tools.try_media --proxy http://127.0.0.1:10809
#   python -m apps.parser.tools.try_media --delete               — после проверки удалить файл из S3
#
# Второй запуск с тем же артикулом должен сказать «уже есть» и ничего не качать.

import argparse
import asyncio
import json
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from apps.parser.goldapple.extractor import extract
from apps.parser.goldapple.normalizer import normalize
from apps.parser.media import ImageUploader
from apps.parser.proxy.models import Proxy
from apps.parser.proxy.source import parse_proxy
from infrastructure.s3.service import S3Service, s3_service

DEFAULT_ARTICLE = "9400200001"

FIXTURES_DIR = Path(__file__).parents[3] / "tests" / "parser" / "fixtures"


class VerboseStorage:
    """
    S3Service с печатью: что спросили у хранилища и что оно ответило.
    """

    def __init__(self, s3: S3Service):
        self.s3 = s3

    async def file_exists(self, object_key: str) -> dict:
        print(f"  S3 file_exists({object_key})...", end=" ", flush=True)
        started = time.monotonic()
        result = await self.s3.file_exists(object_key)
        print(f"status={result['status_code']} ({time.monotonic() - started:.1f} с)")
        return result

    async def upload_file(
        self, file_data: bytes, object_key: str, extension: str
    ) -> dict:
        print(
            f"  S3 upload_file({object_key}, {len(file_data)} байт, {extension})...",
            end=" ",
            flush=True,
        )
        started = time.monotonic()
        result = await self.s3.upload_file(file_data, object_key, extension)
        print(
            f"status={result['status_code']}, error={result['error']} ({time.monotonic() - started:.1f} с)"
        )
        return result


class VerboseUploader(ImageUploader):
    """
    ImageUploader с печатью скачивания. Логику не меняем — только вызываем родителя.
    """

    async def download(
        self, image_link: str, proxy: Proxy | None = None
    ) -> bytes | None:
        print("  качаю картинку с CDN...", end=" ", flush=True)
        started = time.monotonic()
        data = await super().download(image_link, proxy)
        size = "не скачалась" if data is None else f"{len(data)} байт"
        print(f"{size} ({time.monotonic() - started:.1f} с)")
        return data


async def main(article: str, proxy_line: str | None, delete: bool) -> None:
    fixture = FIXTURES_DIR / f"{article}.json"
    card = json.loads(fixture.read_text(encoding="utf-8"))
    product = normalize(extract(card, f"https://goldapple.ru/{article}"))
    print(f"Товар: {product.brand} {product.name}")
    print(f"Картинка: {product.image_link}")

    proxy = parse_proxy(proxy_line) if proxy_line else None
    print(f"Прокси: {proxy or 'нет, напрямую'}")

    s3 = s3_service
    print(f"Хранилище: {s3.endpoint_url}, бакет {s3.bucket_name}\n")

    uploader = VerboseUploader(VerboseStorage(s3))
    image_key = await uploader.upload(product.image_link, product.article_ga, proxy)
    print(f"\nimage_key = {image_key}")
    if image_key:
        print(f"Ссылка: {s3.endpoint_url}/{s3.bucket_name}/{image_key}")

    if delete and image_key:
        result = await s3.delete_file(image_key)
        print(f"Удалила из S3: status={result['status_code']}, error={result['error']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--article", default=DEFAULT_ARTICLE, help="артикул = имя фикстуры"
    )
    parser.add_argument(
        "--proxy", help="прокси, например http://127.0.0.1:10809; без него — напрямую"
    )
    parser.add_argument(
        "--delete", action="store_true", help="после проверки удалить файл из S3"
    )
    args = parser.parse_args()

    asyncio.run(main(article=args.article, proxy_line=args.proxy, delete=args.delete))
