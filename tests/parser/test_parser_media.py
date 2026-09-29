# Тесты ImageUploader: картинка → хранилище → image_key.
# Вместо S3 — хранилище в памяти, скачивание подменяем (сеть не нужна).

import pytest

from apps.parser.media import ImageUploader, extension_from_link
from apps.parser.proxy.models import Proxy, ProxyProtocol

IMAGE_LINK = "https://cdn-01.goldapple.ru/p/p/19000002015/web/abcfullhd.jpg"
IMAGE_BYTES = b"\xff\xd8\xff fake jpeg"
PROXY = Proxy("127.0.0.1", 10809, ProxyProtocol.HTTP)


class MemoryStorage:
    """
    Хранилище в памяти с теми же методами, что у S3Service.
    """

    def __init__(self, upload_error: str | None = None) -> None:
        self.files: dict[str, bytes] = {}
        self.upload_error = upload_error

    async def file_exists(self, object_key: str) -> dict:
        status_code = 200 if object_key in self.files else 404
        return {"status_code": status_code, "etag": None, "error": None}

    async def upload_file(
        self,
        file_data: bytes,
        object_key: str,
        extension: str,
    ) -> dict:
        if self.upload_error:
            return {"status_code": None, "etag": None, "error": self.upload_error}
        self.files[object_key] = file_data
        return {"status_code": 200, "etag": "etag", "error": None}


@pytest.fixture
def downloads(monkeypatch):
    """
    Подменяет ImageUploader.download: отдаёт IMAGE_BYTES и запоминает вызовы.
    """
    calls: list[tuple[str, Proxy | None]] = []

    async def fake_download(self, image_link, proxy=None):
        calls.append((image_link, proxy))
        return IMAGE_BYTES

    monkeypatch.setattr(ImageUploader, "download", fake_download)
    return calls


@pytest.mark.parametrize(
    "link, expected",
    [
        (IMAGE_LINK, "jpg"),
        ("https://cdn/p/abc.PNG", "png"),
        ("https://cdn/p/abc.webp?v=2", "webp"),
        ("https://cdn/p/abc", "jpg"),
    ],
)
def test_extension_from_link(link, expected):
    """
    Расширение из пути ссылки, в нижнем регистре; нет расширения → jpg.
    """
    assert extension_from_link(link) == expected


async def test_upload_new_image(downloads):
    """
    Картинки нет в хранилище → качаем через переданный прокси и заливаем.
    """
    storage = MemoryStorage()

    image_key = await ImageUploader(storage).upload(IMAGE_LINK, "19000002015", PROXY)

    assert image_key == "images/19000002015.jpg"
    assert storage.files == {"images/19000002015.jpg": IMAGE_BYTES}
    assert downloads == [(IMAGE_LINK, PROXY)]


async def test_existing_image_not_downloaded(downloads):
    """
    Картинка уже в хранилище → ключ сразу, не качаем и не заливаем.
    """
    storage = MemoryStorage()
    storage.files["images/19000002015.jpg"] = b"old"

    image_key = await ImageUploader(storage).upload(IMAGE_LINK, "19000002015")

    assert image_key == "images/19000002015.jpg"
    assert storage.files["images/19000002015.jpg"] == b"old"
    assert downloads == []


@pytest.mark.parametrize(
    "image_link, article",
    [(None, "19000002015"), ("", "19000002015"), (IMAGE_LINK, None)],
)
async def test_no_link_or_article(image_link, article, downloads):
    """
    Нет ссылки или артикула → None, в сеть не идём.
    """
    image_key = await ImageUploader(MemoryStorage()).upload(image_link, article)

    assert image_key is None
    assert downloads == []


async def test_download_failed(monkeypatch):
    """
    Картинка не скачалась → None, в хранилище ничего.
    """

    async def failed_download(self, image_link, proxy=None):
        return None

    monkeypatch.setattr(ImageUploader, "download", failed_download)
    storage = MemoryStorage()

    image_key = await ImageUploader(storage).upload(IMAGE_LINK, "19000002015")

    assert image_key is None
    assert storage.files == {}


async def test_upload_failed(downloads):
    """
    Хранилище вернуло ошибку → None.
    """
    storage = MemoryStorage(upload_error="S3 недоступен")

    image_key = await ImageUploader(storage).upload(IMAGE_LINK, "19000002015")

    assert image_key is None
