# Тесты Celery-задачи парсинга run_parse_product_task без БД и сети.
# sync_session, SyncProductRepository и парсер подменены: проверяем,
# какой fill_status и last_error задача ставит продукту в каждом исходе.

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from apps.parser.dto import ParsedProduct
from apps.parser.exceptions import NoAliveProxy, ProductNotFound
from apps.products.models import Product, ProductFillStatus
from apps.products.product_service import CRITICAL_FIELDS
from infrastructure.celery import tasks

LINK = "https://goldapple.ru/19000002015-moisture-surge-100h"


class FakeRepository:
    """
    Репозиторий в памяти: один продукт, update пишет поля в объект.
    """

    def __init__(self, product: Product | None):
        self.product = product
        self.statuses = []

    def get_by_id(self, entity_id: int) -> Product | None:
        return self.product

    def update(self, entity_id: int, data: dict) -> Product:
        for key, value in data.items():
            setattr(self.product, key, value)
        if "fill_status" in data:
            self.statuses.append(data["fill_status"])
        return self.product


class FakeParser:
    """
    Парсер, который отдаёт готовый результат или бросает ошибку.
    """

    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error

    async def parse(self, link: str) -> ParsedProduct:
        if self.error:
            raise self.error
        return self.result


def _run(
    product: Product | None, parser: FakeParser, lock_free: bool = True
) -> FakeRepository:
    """
    Запускает задачу с подменённой сессией, репозиторием, парсером и Redis-lock.
    lock_free=False — lock уже занят другой задачей.
    """
    repository = FakeRepository(product)

    @contextmanager
    def fake_session():
        yield MagicMock()

    @contextmanager
    def fake_lock(lock_name, expire):
        assert lock_name == "parse_lock:1"
        yield lock_free

    with (
        patch.object(tasks, "redis_lock", fake_lock),
        patch.object(tasks, "sync_session", fake_session),
        patch.object(tasks, "SyncProductRepository", lambda session: repository),
        patch.object(tasks, "_get_parser", lambda: parser),
    ):
        tasks.run_parse_product_task(product_id=1)
    return repository


def _full_parsed() -> ParsedProduct:
    """
    ParsedProduct, в котором заполнены все критичные поля.
    """
    data = {name: "x" for name in CRITICAL_FIELDS if name != "link_ga"}
    return ParsedProduct(link_ga=LINK, **data)


def test_all_critical_fields_done():
    """
    Все критичные поля спарсены → IN_PROGRESS, потом DONE, last_error пустой.
    """
    product = Product(link_ga=LINK)
    repository = _run(product, FakeParser(result=_full_parsed()))

    assert repository.statuses == [ProductFillStatus.IN_PROGRESS]
    assert product.fill_status == ProductFillStatus.DONE
    assert product.last_error is None
    assert product.name == "x"


def test_missing_critical_field_incomplete():
    """
    Не хватает критичного поля → INCOMPLETE, в last_error — каких полей нет.
    """
    product = Product(link_ga=LINK)
    parsed = _full_parsed()
    parsed.price_rub = None

    _run(product, FakeParser(result=parsed))

    assert product.fill_status == ProductFillStatus.INCOMPLETE
    assert "price_rub" in product.last_error


def test_parser_error_failed():
    """
    ParserError (NoAliveProxy, ProductNotFound, ParseError) → FAILED + текст в last_error.
    """
    product = Product(link_ga=LINK)
    _run(product, FakeParser(error=ProductNotFound("нет товара")))

    assert product.fill_status == ProductFillStatus.FAILED
    assert product.last_error == "ProductNotFound: нет товара"


def test_no_alive_proxy_failed():
    """
    Прокси кончились → FAILED, повторный запрос сможет парсить заново.
    """
    product = Product(link_ga=LINK)
    _run(product, FakeParser(error=NoAliveProxy("пул пуст")))

    assert product.fill_status == ProductFillStatus.FAILED
    assert product.last_error.startswith("NoAliveProxy")


def test_unexpected_error_failed():
    """
    Любая другая ошибка → тоже FAILED, продукт не застревает в IN_PROGRESS.
    """
    product = Product(link_ga=LINK)
    _run(product, FakeParser(error=RuntimeError("браузер упал")))

    assert product.fill_status == ProductFillStatus.FAILED
    assert product.last_error == "RuntimeError: браузер упал"


def test_product_not_found_in_db():
    """
    Продукта с таким id нет → задача ничего не делает.
    """
    repository = _run(None, FakeParser(result=_full_parsed()))

    assert repository.statuses == []


def test_lock_busy_skips():
    """
    Lock занят (ссылку уже парсит другая задача) → продукт не трогаем.
    """
    product = Product(link_ga=LINK)
    repository = _run(product, FakeParser(result=_full_parsed()), lock_free=False)

    assert repository.statuses == []
    assert product.name is None


def test_already_done_skips():
    """
    Продукт уже DONE (RabbitMQ отдал задачу повторно) → не парсим заново.
    """
    product = Product(link_ga=LINK, fill_status=ProductFillStatus.DONE)
    repository = _run(product, FakeParser(error=RuntimeError("не должен вызываться")))

    assert repository.statuses == []
    assert product.fill_status == ProductFillStatus.DONE


# === _get_parser: один парсер на процесс, пустой пул перечитывается ===


def test_get_parser_reuses_and_reloads_empty_pool(tmp_path):
    """
    Второй вызов отдаёт тот же парсер; пул опустел → proxies.txt читается заново.
    """
    proxies_file = tmp_path / "proxies.txt"
    proxies_file.write_text("http://1.1.1.1:80\nhttp://2.2.2.2:80\n")

    with (
        patch.object(tasks, "_parser", None),
        patch.object(tasks.settings, "PARSER_PROXIES_FILE", str(proxies_file)),
    ):
        first = tasks._get_parser()
        assert tasks._get_parser() is first
        assert len(first.pool) == 2

        for proxy in list(first.pool._proxies):
            first.pool.mark_bad(proxy)
        assert len(first.pool) == 0

        reloaded = tasks._get_parser()
        assert reloaded is not first
        assert len(reloaded.pool) == 2
