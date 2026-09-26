# apps/parser/media.py

# Картинка товара: ссылка с сайта → файл в хранилище → image_key.

# Парсер сам в S3 не ходит: хранилище передают снаружи (S3Service),
# парсер знает только два его метода — file_exists и upload_file.
# Ключ придумываем здесь: images/<артикул>.<расширение>. Ключ всегда один и тот же,
# поэтому при повторном парсинге картинка второй раз не заливается.

# Картинки лежат на CDN (cdn-01.goldapple.ru), антибота там нет:
# curl без браузера → 200 image/jpeg. Поэтому качаем через httpx, а не Playwright.

# Не скачалась или не загрузилась → None. Парсинг из-за картинки не падает:
# товар без image_key станет INCOMPLETE — это решает модуль товаров.

from pathlib import PurePosixPath
from typing import Protocol
from urllib.parse import urlsplit

import httpx
from socksio.exceptions import ProtocolError as SocksProtocolError

from apps.parser.proxy.models import Proxy

# Папка в бакете
IMAGE_PREFIX = "images"

# В ссылке нет расширения → считаем jpg: extractor и так просит у CDN jpg
DEFAULT_EXTENSION = "jpg"

# Сколько ждём картинку, секунд. Картинка ~400 КБ, через бесплатный прокси — долго
DEFAULT_TIMEOUT = 30.0

# Обычный Chrome, как в клиенте
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
)


class ImageStorage(Protocol):
    """
    Хранилище картинок — всё, что парсеру нужно от S3Service.

    Protocol: наследоваться не надо, подходит любой класс с такими методами.
    В тестах вместо S3 подставляем свой класс в памяти.
    """

    async def file_exists(
            self,
            object_key: str,
    ) -> dict: ...

    async def upload_file(
            self,
            file_data: bytes,
            object_key: str,
            extension: str,
    ) -> dict: ...


class ImageUploader:
    """
    Скачивает картинку товара и кладёт её в хранилище.
    """

    def __init__(
            self,
            storage: ImageStorage,
            timeout: float = DEFAULT_TIMEOUT,
    ):
        """
        :param storage: хранилище (S3Service), передаётся снаружи
        :param timeout: сколько ждать картинку, секунд
        """
        self.storage = storage
        self.timeout = timeout

    async def upload(
            self,
            image_link: str | None,
            article: str | None,
            proxy: Proxy | None = None,
    ) -> str | None:
        """
        Картинка по ссылке → ключ в хранилище. Не получилось → None.

        :param image_link: ссылка на картинку с сайта
        :param article: артикул товара, из него ключ
        :param proxy: через какой прокси качать; None — напрямую
        """
        if not image_link or not article:
            return None

        extension = extension_from_link(image_link)
        image_key = f"{IMAGE_PREFIX}/{article}.{extension}"

        # Уже лежит в хранилище — не качаем и не заливаем заново
        exists = await self.storage.file_exists(image_key)
        if exists["status_code"] == 200:
            return image_key

        file_data = await self.download(image_link, proxy)
        if file_data is None:
            return None

        result = await self.storage.upload_file(file_data, image_key, extension)
        if result["error"]:
            return None
        return image_key

    async def download(
            self,
            image_link: str,
            proxy: Proxy | None = None,
    ) -> bytes | None:
        """
        Скачивает картинку. Не картинка, ошибка сети, плохой статус → None.

        :param image_link: ссылка на картинку
        :param proxy: через какой прокси качать; None — напрямую
        """
        proxy_server = proxy.server if proxy else None
        try:
            async with httpx.AsyncClient(
                    proxy=proxy_server,
                    timeout=self.timeout,
                    headers={"User-Agent": USER_AGENT},
                    follow_redirects=True,
            ) as client:
                response = await client.get(image_link)
                response.raise_for_status()
        except httpx.HTTPError:
            # не подключился, таймаут, плохой статус
            return None
        except SocksProtocolError:
            # сломанный SOCKS5-прокси, httpx эту ошибку не заворачивает
            return None

        # Вместо картинки могли прислать HTML (страница ошибки, заглушка прокси)
        content_type = response.headers.get("content-type", "")
        if not content_type.startswith("image/"):
            return None
        return response.content


def extension_from_link(image_link: str) -> str:
    """
    Расширение из ссылки: «…/abcfullhd.jpg» → «jpg». Нет расширения → «jpg».

    :param image_link: ссылка на картинку
    """
    path = urlsplit(image_link).path
    extension = PurePosixPath(path).suffix.lstrip(".").lower()
    if not extension:
        return DEFAULT_EXTENSION
    return extension
