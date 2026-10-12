# Тесты Celery-задачи парсинга run_parse_product_task без БД и сети.
# sync_session, SyncProductRepository и парсер подменены: проверяем,
# какой fill_status и last_error задача ставит продукту в каждом исходе.

from contextlib import contextmanager
from datetime import datetime, timezone
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
        # fill_status продукта в момент, когда задача двинула подборки
        self.continued = []

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
        patch.object(
            tasks,
            "_continue_selections_after_parse",
            lambda session, product: repository.continued.append(product.fill_status),
        ),
    ):
        tasks.run_parse_product_task(product_id=1)
    return repository


def _full_parsed() -> ParsedProduct:
    """
    ParsedProduct, в котором заполнены все критичные поля.
    """
    data = {name: "x" for name in CRITICAL_FIELDS if name != "product_link"}
    return ParsedProduct(product_link=LINK, **data)


def test_all_critical_fields_done():
    """
    Все критичные поля спарсены → IN_PROGRESS, потом DONE, last_error пустой.
    """
    product = Product(product_link=LINK)
    repository = _run(product, FakeParser(result=_full_parsed()))

    assert repository.statuses == [ProductFillStatus.IN_PROGRESS]
    assert product.fill_status == ProductFillStatus.DONE
    assert product.last_error is None
    assert product.name == "x"
    assert repository.continued == [ProductFillStatus.DONE]


def test_missing_critical_field_incomplete():
    """
    Не хватает критичного поля → INCOMPLETE, в last_error — каких полей нет.
    """
    product = Product(product_link=LINK)
    parsed = _full_parsed()
    parsed.price_rub = None

    repository = _run(product, FakeParser(result=parsed))

    assert product.fill_status == ProductFillStatus.INCOMPLETE
    assert "price_rub" in product.last_error
    assert repository.continued == [ProductFillStatus.INCOMPLETE]


def test_parser_error_failed():
    """
    ParserError (NoAliveProxy, ProductNotFound, ParseError) → FAILED + текст в last_error.
    """
    product = Product(product_link=LINK)
    repository = _run(product, FakeParser(error=ProductNotFound("нет товара")))

    assert product.fill_status == ProductFillStatus.FAILED
    assert product.last_error == "ProductNotFound: нет товара"
    assert repository.continued == [ProductFillStatus.FAILED]


def test_no_alive_proxy_failed():
    """
    Прокси кончились → FAILED, повторный запрос сможет парсить заново.
    """
    product = Product(product_link=LINK)
    _run(product, FakeParser(error=NoAliveProxy("пул пуст")))

    assert product.fill_status == ProductFillStatus.FAILED
    assert product.last_error.startswith("NoAliveProxy")


def test_unexpected_error_failed():
    """
    Любая другая ошибка → тоже FAILED, продукт не застревает в IN_PROGRESS.
    """
    product = Product(product_link=LINK)
    repository = _run(product, FakeParser(error=RuntimeError("браузер упал")))

    assert product.fill_status == ProductFillStatus.FAILED
    assert product.last_error == "RuntimeError: браузер упал"
    assert repository.continued == [ProductFillStatus.FAILED]


def test_product_not_found_in_db():
    """
    Продукта с таким id нет → задача ничего не делает.
    """
    repository = _run(None, FakeParser(result=_full_parsed()))

    assert repository.statuses == []
    assert repository.continued == []


def test_lock_busy_skips():
    """
    Lock занят (ссылку уже парсит другая задача) → продукт не трогаем.
    """
    product = Product(product_link=LINK)
    repository = _run(product, FakeParser(result=_full_parsed()), lock_free=False)

    assert repository.statuses == []
    assert product.name is None
    assert repository.continued == []


def test_already_done_skips():
    """
    Продукт уже DONE (RabbitMQ отдал задачу повторно) → не парсим заново,
    но подборки, оставшиеся в PARSING, двигаем дальше.
    """
    product = Product(product_link=LINK, fill_status=ProductFillStatus.DONE)
    repository = _run(product, FakeParser(error=RuntimeError("не должен вызываться")))

    assert repository.statuses == []
    assert product.fill_status == ProductFillStatus.DONE
    assert repository.continued == [ProductFillStatus.DONE]


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


# === _continue_selections_after_parse: подборки PARSING после парсинга ===


class FakeSession:
    """
    Сессия, которая на каждый execute отдаёт заданные id и запоминает запросы.
    """

    def __init__(self, rows):
        self.rows = rows
        self.statements = []
        self.commits = 0

    def execute(self, statement):
        self.statements.append(statement)
        result = MagicMock()
        result.scalars.return_value.all.return_value = self.rows
        return result

    def commit(self):
        self.commits += 1


def _continue(product: Product, selection_ids: list[int]):
    """
    Запускает _continue_selections_after_parse с подменённой генерацией и возвратом круток.
    """
    session = FakeSession(selection_ids)
    generation = MagicMock()
    release = MagicMock()

    with (
        patch.object(tasks.run_create_selection_on_task, "delay", generation),
        patch.object(tasks, "_release_spins_for_selection", release),
    ):
        tasks._continue_selections_after_parse(session, product)
    return session, generation, release


def test_continue_done_queue_and_generation():
    """
    Продукт DONE → подборки QUEUE, коммит, генерация на каждую, крутки не трогаем.
    """
    product = Product(id=1, product_link=LINK, fill_status=ProductFillStatus.DONE)
    session, generation, release = _continue(product, [5, 6])

    params = session.statements[0].compile().params
    assert params["selection_status"] == tasks.SelectionStatus.QUEUE
    assert session.commits == 1
    assert [c.kwargs for c in generation.call_args_list] == [
        {"selection_id": 5},
        {"selection_id": 6},
    ]
    release.assert_not_called()


def test_continue_failed_selection_failed_and_release():
    """
    Продукт FAILED → подборки FAILED с причиной, ожидающим возвращается крутка.
    """
    product = Product(
        id=1,
        product_link=LINK,
        fill_status=ProductFillStatus.FAILED,
        last_error="NoAliveProxy: пул пуст",
    )
    session, generation, release = _continue(product, [5])

    params = session.statements[0].compile().params
    assert params["selection_status"] == tasks.SelectionStatus.FAILED
    assert params["error_message"] == "NoAliveProxy: пул пуст"
    assert session.commits == 1
    release.assert_called_once_with(session, 5)
    generation.assert_not_called()


def test_continue_incomplete_selection_failed():
    """
    Продукт INCOMPLETE → подборки тоже FAILED, генерацию не запускаем.
    """
    product = Product(
        id=1,
        product_link=LINK,
        fill_status=ProductFillStatus.INCOMPLETE,
        last_error="Не хватает полей: price_rub",
    )
    session, generation, release = _continue(product, [5])

    params = session.statements[0].compile().params
    assert params["selection_status"] == tasks.SelectionStatus.FAILED
    generation.assert_not_called()


# === _check_stuck_parsing: beat-страховка для PARSING ===


def _check_stuck(selections: list) -> tuple[MagicMock, MagicMock]:
    """
    Запускает _check_stuck_parsing на заданных «зависших» подборках.
    """
    session = FakeSession(selections)
    continue_mock = MagicMock()
    parse = MagicMock()

    with (
        patch.object(tasks, "_continue_selections_after_parse", continue_mock),
        patch.object(tasks.run_parse_product_task, "delay", parse),
    ):
        tasks._check_stuck_parsing(session)
    return continue_mock, parse


def _stuck_selection(product: Product) -> MagicMock:
    """
    Подборка в PARSING с давним updated_at.
    """
    selection = MagicMock()
    selection.product_id = product.id
    selection.product = product
    selection.updated_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return selection


def test_stuck_parsing_product_done_continues():
    """
    Продукт уже DONE (задача упала после парсинга) → двигаем подборки, не парсим.
    """
    product = Product(id=1, product_link=LINK, fill_status=ProductFillStatus.DONE)
    continue_mock, parse = _check_stuck([_stuck_selection(product)])

    continue_mock.assert_called_once()
    assert continue_mock.call_args.args[1] is product
    parse.assert_not_called()


def test_stuck_parsing_product_failed_continues():
    """
    Продукт FAILED → подборки FAILED через тот же _continue_selections_after_parse.
    """
    product = Product(id=1, product_link=LINK, fill_status=ProductFillStatus.FAILED)
    continue_mock, parse = _check_stuck([_stuck_selection(product)])

    continue_mock.assert_called_once()
    parse.assert_not_called()


def test_stuck_parsing_in_progress_reparse_once():
    """
    Продукт IN_PROGRESS (воркер умер) → парсим заново один раз на продукт,
    даже если подборок две; updated_at сдвигается.
    """
    product = Product(
        id=1, product_link=LINK, fill_status=ProductFillStatus.IN_PROGRESS
    )
    first, second = _stuck_selection(product), _stuck_selection(product)
    continue_mock, parse = _check_stuck([first, second])

    parse.assert_called_once_with(product_id=1)
    continue_mock.assert_not_called()
    assert first.updated_at > datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert second.updated_at == first.updated_at
