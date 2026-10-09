# Команды по парсеру

Все команды можно запускать из любой папки: они сами переходят куда нужно и возвращают в корень проекта.
Каждая команда — одна строка, копировать целиком.

## Вернуться в корень проекта
```
cd ~/Projects/beauty_helper_fastapi
```

## Скачать одну карточку через Playwright
Без окна:
```
cd ~/Projects/beauty_helper_fastapi/apps/parser && python tools/try_playwright.py; cd ~/Projects/beauty_helper_fastapi
```
С окном браузера:
```
cd ~/Projects/beauty_helper_fastapi/apps/parser && python tools/try_playwright.py --headed; cd ~/Projects/beauty_helper_fastapi
```
Другой товар (подставь ссылку и артикул):
```
cd ~/Projects/beauty_helper_fastapi/apps/parser && python tools/try_playwright.py --url "https://goldapple.ru/<артикул>-<название>" --out ../../tests/parser/fixtures/<артикул>.json; cd ~/Projects/beauty_helper_fastapi
```

## Перекачать все фикстуры
```
cd ~/Projects/beauty_helper_fastapi/apps/parser && bash tools/fetch_fixtures.sh; cd ~/Projects/beauty_helper_fastapi
```

## Прокси
Установить httpx с поддержкой SOCKS5 (один раз, в активированном .venv):
```
cd ~/Projects/beauty_helper_fastapi && pip install "httpx[socks]==0.28.1"
```
Найти живой прокси из `apps/parser/proxy/proxies.txt` через пул (ходит только на httpbin.org, не на ЗЯ):
```
cd ~/Projects/beauty_helper_fastapi && python -m apps.parser.tools.check_proxies
```
Если живых нет — проверить, открывается ли httpbin вообще, без прокси (ответ — твой IP в JSON):
```
curl -s --max-time 10 https://httpbin.org/ip
```

## Клиент ЗЯ (шаг 3)
Рабочая ссылка, прокси из пула:
```
cd ~/Projects/beauty_helper_fastapi && python -m apps.parser.tools.try_client
```
Битая ссылка — ждём `ProductNotFound` за секунды, а не `SiteBlocked` через минуту:
```
cd ~/Projects/beauty_helper_fastapi && python -m apps.parser.tools.try_client --url "https://goldapple.ru/19000541119-botavik"
```
То же через свой прокси 127.0.0.1:10809 вместо пула (если бесплатные не пускают):
```
cd ~/Projects/beauty_helper_fastapi && python -m apps.parser.tools.try_client --proxy http://127.0.0.1:10809
```
```
cd ~/Projects/beauty_helper_fastapi && python -m apps.parser.tools.try_client --proxy http://127.0.0.1:10809 --url "https://goldapple.ru/19000541119-botavik"
```
С окном браузера — добавить в конец любой команды ` --headed`.

## Товар с несколькими объёмами (шаг 5, проверка выбора варианта)
L'Interdit 50 мл — смотрим, есть ли в одном JSON все объёмы:
```
cd ~/Projects/beauty_helper_fastapi/apps/parser && python tools/try_playwright.py --url "https://goldapple.ru/3680300002-l-interdit" --out ../../tests/parser/fixtures/3680300002.json; cd ~/Projects/beauty_helper_fastapi
```

## Normalizer (шаг 6)
Установить BeautifulSoup (один раз, в активированном .venv):
```
cd ~/Projects/beauty_helper_fastapi && pip install "beautifulsoup4==4.15.0"
```

## Картинка (шаг 7, проверка: отдаёт ли CDN картинку без браузера)
Ждём `200 image/jpeg` и размер в байтах. `403` или `text/html` — CDN тоже под антиботом.
```
cd ~/Projects/beauty_helper_fastapi && curl -sS -o /dev/null -w "%{http_code} %{content_type} %{size_download}\n" -A "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36" "https://cdn-01.goldapple.ru/p/p/9400200001/web/696d674d61696e5064705f32636330366166366561313834626166393865656130356537633333623330638dea5fc09907d3afullhd.jpg"
```

## Картинка (шаг 7, ручная проверка ImageUploader на CDN и настоящем S3)
Ссылку берёт из фикстуры, на сайт ЗЯ не ходит. Кладёт в бакет `images/9400200001.jpg`.
Первый запуск — качает и заливает:
```
cd ~/Projects/beauty_helper_fastapi && python -m apps.parser.tools.try_media
```
Второй запуск — должен сказать `status=200` на file_exists и ничего не качать; `--delete` в конце убирает файл из бакета:
```
cd ~/Projects/beauty_helper_fastapi && python -m apps.parser.tools.try_media --delete
```

## Сборка parse (шаг 8, вся цепочка: сайт → ParsedProduct → картинка в S3)
Рабочая ссылка, прокси из пула:
```
cd ~/Projects/beauty_helper_fastapi && python -m apps.parser.tools.try_parse
```
Через свой прокси 127.0.0.1:10809:
```
cd ~/Projects/beauty_helper_fastapi && python -m apps.parser.tools.try_parse --proxy http://127.0.0.1:10809
```
Битая ссылка — ждём `ProductNotFound`:
```
cd ~/Projects/beauty_helper_fastapi && python -m apps.parser.tools.try_parse --proxy http://127.0.0.1:10809 --url "https://goldapple.ru/19000541119-botavik"
```

## Тесты парсера (шаг 9, без сети)
```
cd ~/Projects/beauty_helper_fastapi && python -m pytest tests/parser -q
```

## Docker: браузер в образе (шаг 11)
Пересобрать и поднять (как `make up`):
```
cd ~/Projects/beauty_helper_fastapi && docker compose -f docker/docker-compose.yaml --env-file .env up -d --build
```
Проверить, что headless Chromium запускается внутри воркера (ждём `chromium ok`):
```
cd ~/Projects/beauty_helper_fastapi && docker exec bh_celery python -c "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); b = p.chromium.launch(); print('chromium ok', b.version); b.close(); p.stop()"
```

## Миграция: статус подборки PARSING (встраивание, шаг 2)
Применить (то же делает entrypoint при старте контейнера):
```
cd ~/Projects/beauty_helper_fastapi && docker exec bh_backend alembic upgrade head
```
Проверить, что PARSING появился в enum (ждём `PARSING` в списке; пользователь и база — из `.env`, через окружение контейнера):
```
cd ~/Projects/beauty_helper_fastapi && docker exec bh_pg sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT unnest(enum_range(NULL::selection_status));"'
```

## pre-commit: ruff перед каждым коммитом
Поставить и подключить хук (разово, в .venv):
```
cd ~/Projects/beauty_helper_fastapi && pip install -r requirements-dev.txt && pre-commit install
```
Проверить, что всё чисто (ждём `Passed` у ruff и ruff-format):
```
cd ~/Projects/beauty_helper_fastapi && pre-commit run --all-files
```

## Оркестратор: платный парсинг (09.10)
Поднять БД и прогнать тесты оркестратора (ждём `passed` без `skipped`):
```
cd ~/Projects/beauty_helper_fastapi && make up-db && python -m pytest -q -rs tests/test_orchestrator.py
```
Статус парсинга и подборки по ссылке (ждём `IN_PROGRESS`/`PARSING` → `DONE`/`QUEUE` → `DONE`/`DONE`; подставь артикул из ссылки):
```
cd ~/Projects/beauty_helper_fastapi && docker exec bh_pg sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT p.id, p.fill_status, p.last_error, s.id AS sel, s.selection_status, s.error_message FROM products p JOIN selections s ON s.product_id = p.id WHERE p.link_ga LIKE '"'"'%25270500001%'"'"';"'
```
Перезапустить воркер после правок кода (Celery сам код не перечитывает) и смотреть логи парсинга:
```
cd ~/Projects/beauty_helper_fastapi && docker restart bh_celery && docker logs -f --since 1m bh_celery 2>&1 | grep -E "PARSE|PROXY|SELECTION|ERROR"
```
