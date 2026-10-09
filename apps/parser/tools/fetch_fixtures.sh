#!/bin/bash
# Скачивает JSON карточек для фикстур: 4 товара из Excel + 1 не в наличии.
# (meraki 19000480746 снята отдельно, её здесь нет)
# Запуск из папки apps/parser: bash tools/fetch_fixtures.sh

URLS=(
    "https://goldapple.ru/19000002015-moisture-surge-100h"
    "https://goldapple.ru/9400200001-bamboo-creme-frappee"
    "https://goldapple.ru/19000044476-aloe-waterproof-sun-cream-spf-50-pa"
    "https://goldapple.ru/9410400008-pomegranate-nutri-moisturizing-cream"
    "https://goldapple.ru/19000074476-101b-hair-shedding-proof-tonic"
)

for url in "${URLS[@]}"; do
    article=$(basename "$url" | cut -d- -f1)
    echo "=== $article"
    python tools/try_playwright.py --url "$url" --out "../../tests/parser/fixtures/$article.json"
done
