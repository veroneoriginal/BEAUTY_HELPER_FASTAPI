# apps/parser/tools/try_playwright.py

# Проба шага 1 (разведка): проходит ли Playwright антибот Золотого Яблока.
# Открывает страницу товара в Chromium, браузер сам проходит JS-проверку
# и запрашивает product-card/base/v3. Мы перехватываем этот ответ
# и сохраняем JSON в файл.
#
# Браузер чистый: без твоих cookies и без входа в аккаунт.
#
# Запуск (из папки apps/parser):
#   python tools/try_playwright.py                — без окна (headless)
#   python tools/try_playwright.py --headed        — с окном, видно, что происходит
#   python tools/try_playwright.py --url <ссылка>   — другой товар
#   python tools/try_playwright.py --url <ссылка> --out ../../tests/parser/fixtures/x.json — куда сохранить JSON

import argparse
import asyncio
import json
from pathlib import Path

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

DEFAULT_URL = "https://goldapple.ru/19000480746-mytaui-meraki"

# Запросы идут через прокси браузера, а не с домашнего IP
PROXY = "http://127.0.0.1:10809"

# Кусок адреса запроса, в котором лежит карточка товара
CARD_API_PART = "/front/api/catalog/product-card/base/v3"

TOOLS_DIR = Path(__file__).parent
OUTPUT_FILE = (
    TOOLS_DIR.parents[2] / "tests" / "parser" / "fixtures" / "19000480746.json"
)
# HTML страницы на случай, если карточка пришла не через API (в .gitignore)
PAGE_FILE = TOOLS_DIR / "debug_page.html"


async def fetch_card(url: str, headed: bool, output_file: Path) -> None:
    """
    Открывает страницу товара и ловит ответ API карточки.

    :param url: ссылка на товар
    :param headed: True — показать окно браузера
    :param output_file: куда сохранить JSON карточки
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=not headed,
            proxy={"server": PROXY},
        )
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

        # Диагностика: печатаем все запросы к API сайта
        page.on(
            "response",
            lambda r: (
                print(f"  [api] {r.status} {r.url[:120]}")
                if "/front/api/" in r.url
                else None
            ),
        )
        print(f"User-Agent: {await page.evaluate('navigator.userAgent')}")

        try:
            # Ждём нужный ответ, пока страница грузится
            async with page.expect_response(
                lambda r: CARD_API_PART in r.url,
                timeout=60_000,
            ) as response_info:
                await page.goto(url, wait_until="domcontentloaded")

            response = await response_info.value
            print(f"Статус ответа API: {response.status}")

            if response.status != 200:
                print("Антибот не пропустил. Попробуй с --headed.")
                return

            data = await response.json()
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            product = data.get("data", {})
            print(f"Товар: {product.get('brand')} {product.get('name')}")
            print(f"Сохранено: {output_file}")

        except PlaywrightTimeoutError:
            print("За 60 секунд запрос карточки так и не появился.")
            print(f"Заголовок страницы: {await page.title()!r}")
            PAGE_FILE.write_text(await page.content(), encoding="utf-8")
            print(f"HTML страницы сохранён: {PAGE_FILE}")
        finally:
            await browser.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--out", type=Path, default=OUTPUT_FILE)
    args = parser.parse_args()

    asyncio.run(fetch_card(url=args.url, headed=args.headed, output_file=args.out))


if __name__ == "__main__":
    main()
