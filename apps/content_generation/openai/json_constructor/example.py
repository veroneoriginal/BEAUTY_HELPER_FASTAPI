# apps/content_generation/openai/json_constructor/example.py
# Предположительно, будет такой словарь приходить с фронта

# Если пользователь выбрал 1 средство

request_info = {
    "user_id": "user_telegram_id",
    "task_type": "Разбор состава одного средства",
    "products": {
        "product_1": "ссылка на продукт",
    },
}

# Далее, обрабатываем пришедший словарь и дополняем
processed_request_info = {
    "user_id": "user_telegram_id",
    "task_type": "Разбор состава одного средства",
    "products": {
        "product_1": {
            "category": "product.category",
            "ingredients_list": "product.ingredients_list",
        }
    },
}

# Преобразованный в соответствии с кодом задачи словарь
update_request_info = {
    "task_type": "Подробный анализ каждого элемента состава",
    "name": "Шампунь магический современный",
    "product_type_detailed": "Шампунь",
    "article_ga": "43347287037",
    "ingredients_list": [
        "Aqua",
        "Cocamidopropyl Betaine",
        "Sodium Laureth Sulfate",
        "Glycerin",
    ],
    "ingredients_count": 4,
}

# Если пользователь выбрал несколько средств
request_info_a_lot = {
    "user_id": " ",
    "task_type": "",
    "products": {
        "product_1": "ссылка на продукт",
        "product_2": "ссылка на продукт",
        "product_3": "ссылка на продукт",
    },
}

# Далее, обрабатываем пришедший словарь, чтобы по каждому средству была инфа

# Далее, обрабатываем пришедший словарь и дополняем
processed_request_info_a_lot = {
    "user_id": "user_telegram_id",
    "task_type": "код задачи",
    "products": {
        "product_1": {
            "ingredients_list": "product.ingredients_list",
        },
        "product_2": {
            "ingredients_list": "product.ingredients_list",
        },
    },
}
