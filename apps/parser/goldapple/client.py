# apps/parser/goldapple/client.py

# Клиент Золотого Яблока: по ссылке на товар отдаёт сырой JSON карточки.
#
# HTML страницы пустой, данные приходят из API product-card/base/v3,
# а антибот пускает только настоящий браузер. Поэтому:
#   Playwright открывает страницу через прокси → браузер сам проходит JS-проверку
#   и запрашивает API → мы перехватываем этот ответ и отдаём его JSON.
#
# Прокси выбирает не клиент: его передают снаружи (из ProxyPool.get()).
# Сайт не пустил → SiteBlocked, вызывающий код делает mark_bad и берёт другой.

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from apps.parser.exceptions import ParseError, ProductNotFound, SiteBlocked
from apps.parser.proxy.models import Proxy

# Кусок адреса запроса, в котором лежит карточка товара
CARD_API_PART = "/front/api/catalog/product-card/base/v3"

# Битая ссылка: страница отвечает 200, карточку не запрашивает,
# а рисует «упс... страница не найдена» и грузит для неё рекомендации
# запросом placements?...&requestSource=errorPage. По нему и узнаём (24.09).
ERROR_PAGE_PART = "requestSource=errorPage"

# Сколько ждём карточку, секунд.
# Через бесплатный прокси страница грузится долго.
DEFAULT_TIMEOUT = 60.0


async def fetch(
    link: str,
    proxy: Proxy,
    timeout: float = DEFAULT_TIMEOUT,
    headless: bool = True,
) -> dict:
    """
    Открывает страницу товара и возвращает JSON карточки из API как есть.

    :param link: ссылка на товар
    :param proxy: через какой прокси идём
    :param timeout: сколько ждать карточку, секунд
    :param headless: False — показать окно браузера (для отладки)
    :raises SiteBlocked: 403, обрыв, таймаут — прокси надо менять
    :raises ProductNotFound: битая ссылка — страница «не найдена» или 404
    :raises ParseError: карточка пришла, но это не JSON-объект
    """
    timeout_ms = timeout * 1000

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            proxy={"server": proxy.server},
        )
        try:
            # В headless User-Agent содержит «HeadlessChrome», и сайт отдаёт
            # заранее отрисованную страницу для поисковых ботов, без JS и без API.
            # Подставляем обычный UA Chrome той же версии.
            major_version = browser.version.split(".")[0]
            user_agent = (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                f"(KHTML, like Gecko) Chrome/{major_version}.0.0.0 Safari/537.36"
            )
            context = await browser.new_context(
                user_agent=user_agent,
                locale="ru-RU",
                timezone_id="Europe/Moscow",
                viewport={"width": 1366, "height": 768},
            )
            page = await context.new_page()

            try:
                # Ждём, что придёт первым: карточка или признак страницы «не найдена»
                async with page.expect_response(
                    lambda r: CARD_API_PART in r.url or ERROR_PAGE_PART in r.url,
                    timeout=timeout_ms,
                ) as response_info:
                    page_response = await page.goto(
                        link,
                        wait_until="domcontentloaded",
                        timeout=timeout_ms,
                    )
                    # Страница сама ответила ошибкой — карточку не ждём
                    _check_status(page_response.status if page_response else None)

                card_response = await response_info.value
            except PlaywrightTimeoutError as e:
                raise SiteBlocked(
                    f"Карточка не пришла за {timeout:.0f} с: {link}"
                ) from e
            except PlaywrightError as e:
                # net::ERR_PROXY_CONNECTION_FAILED, обрыв и т.п.
                raise SiteBlocked(f"Ошибка сети через {proxy}: {e.message}") from e

            if ERROR_PAGE_PART in card_response.url:
                raise ProductNotFound(f"Сайт показал «страница не найдена»: {link}")

            _check_status(card_response.status)

            try:
                data = await card_response.json()
            except (ValueError, PlaywrightError) as e:
                raise ParseError(f"Карточка пришла не в JSON: {link}") from e
        finally:
            await browser.close()

    if not isinstance(data, dict):
        raise ParseError(f"Карточка — не JSON-объект: {link}")

    return data


def _check_status(status: int | None) -> None:
    """
    Статус ответа сайта → наше исключение. 200 и None (ответа нет) пропускаем.

    :param status: HTTP-статус
    :raises ProductNotFound: 404
    :raises SiteBlocked: любой другой код ошибки (403, 5xx)
    """
    if status is None or status < 400:
        return
    if status == 404:
        raise ProductNotFound("Сайт ответил 404: товара нет")
    raise SiteBlocked(f"Сайт ответил {status}")
