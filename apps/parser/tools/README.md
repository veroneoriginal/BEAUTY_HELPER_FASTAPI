# Инструменты парсера

Скрипты для ручной проверки парсера на **живом** сайте Золотого Яблока, CDN и настоящем S3.
В автотесты не входят: автотесты — в `tests/parser/`, без сети, на фикстурах.

Готовые команды одной строкой — в [`commands.md`](commands.md).

## Скрипты

| Скрипт | Что проверяет | Куда ходит |
|---|---|---|
| `check_proxies.py` | пул прокси: загрузить список и получить один живой прокси | httpbin |
| `try_client.py` | клиент `goldapple/client.py`: карточка товара по ссылке, перебор прокси | сайт ЗЯ |
| `try_media.py` | `media.ImageUploader`: картинка с CDN → S3; ссылка на картинку — из фикстуры | CDN, S3 |
| `try_parse.py` | весь `ProductParser.parse`: прокси → карточка → разбор → картинка → `ParsedProduct` | сайт ЗЯ, CDN, S3 |
| `try_playwright.py` | разведка: проходит ли Playwright антибот; сохраняет JSON карточки в фикстуру | сайт ЗЯ |
| `fetch_fixtures.sh` | скачивает карточки для фикстур `tests/parser/fixtures/` (через `try_playwright.py`) | сайт ЗЯ |

## Запуск

Python-скрипты, кроме `try_playwright.py`, — **из корня проекта** как модули:
```
python -m apps.parser.tools.try_parse --url <ссылка>
```

`try_playwright.py` и `fetch_fixtures.sh` — **из папки `apps/parser`**, пути к фикстурам в них относительные:
```
cd apps/parser && python tools/try_playwright.py --url <ссылка> --out ../../tests/parser/fixtures/<артикул>.json
```

## Общие параметры

- `--url` — ссылка на товар (по умолчанию — рабочая ссылка из скрипта).
- `--proxy http://127.0.0.1:10809` — один конкретный прокси вместо пула: отделить поведение сайта
  от капризов бесплатных прокси. В `try_media.py` без `--proxy` картинка качается напрямую.
- `--headed` (`try_client.py`, `try_playwright.py`) — с окном браузера.
- `--delete` (`try_media.py`) — после проверки удалить картинку из S3.

Список прокси — `settings.PARSER_PROXIES_FILE` (по умолчанию `apps/parser/proxy/proxies.txt`).
S3 и остальные настройки — из `.env`.

`try_playwright.py` при неудаче сохраняет HTML страницы в `tools/debug_page.html` (в `.gitignore`).
