# Swagger
http://localhost:8000/docs

Генерит первый пользователь с нуля https://goldapple.ru/19000002015-moisture-surge-100h

А второй отправляем ссылку на это же средство и ему возвращается готовый результат


https://goldapple.ru/9400200001-bamboo-creme-frappee
https://goldapple.ru/19000044476-aloe-waterproof-sun-cream-spf-50-pa
https://goldapple.ru/9410400008-pomegranate-nutri-moisturizing-cream



## Проверяем, что Selection не работает без авторизации.
{
"product_link": "https://goldapple.ru/19000044476-aloe-waterproof-sun-cream-spf-50-pa",
"task_type": "detailed_analysis"
}

### Получаем 401 - {"detail": "Not authenticated"}

## Регистрация пользователя
{
"email": "user_number1@example.com",
"password": "12379796n1"
}

### Получаем 201 Response body
{
"message": "Пользователь зарегистрирован. Проверьте почту для подтверждения email.",
"confirmation_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwidHlwZSI6ImVtYWlsX2NvbmZpcm1hdGlvbiIsImV4cCI6MTc4MTYyMTAxOX0.cMEa67lJAk_NrUOY0fgsiBeNqa0-qJo0pDLFR29mtIE"
}

## Подтверждение емейл
Вставляем токен, который был выдан выше.

### Получаем 200 Response body
{
"message": "Email успешно подтверждён. Теперь вы можете войти."
}

## Вход в акааунт
{
"email": "user_number1@example.com",
"password": "12379796n1"
}

### Получаем 200 Response body
{
"access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiZXhwIjoxNzgxNTM2NDYwLCJ0eXBlIjoiYWNjZXNzIn0.6UUL8YXQRJAS3ce7bmc6p7dUxkGXrmnnif4FntVPhpM",
"refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiZXhwIjoxNzgyMTM5NDYwLCJ0eXBlIjoicmVmcmVzaCJ9.RmqsUqvti3ND4kEG4l3CEvktjfsCu9ffNJD3i-sTdh8",
"token_type": "bearer"
}

## Авторизация справа сверху
Вводим в поле access_token

## Проверка баланса 
Возвращает
{
"user_id": 1,
"spins": 0,
"reserved_spins": 0
}

## Затем покупаем пакет и начисляются генерации
Отправляем {"package_id": 1}
Получаем {"message": "Пакет куплен, генерации начислены"}

## Теперь нужно отправить средство на анализ
{
"product_link": "https://goldapple.ru/9400200001-bamboo-creme-frappee",
"task_type": "detailed_analysis"
}
### Получаем 200 Response body

{
"status": "created",
"message": "Анализируем средство. Мы пришлём PDF когда будет готово.",
"pdf_url": null
}


### Когда подборка готова
{
"status": "done",
"message": "Эта подборка у Вас уже есть. Отправляем PDF.",
"pdf_url": "https://s3.ru1.storage.beget.cloud/181028092d1d-beauty-helper-media/pdf/detailed_analysis_9410400008_24115c6c-9bdc-4f59-a711-2a36a3bb06da.pdf"
}

## Чтобы продемонстрировать подборку, 
нужно зайти в настрйоки Beget и сделать весь материал публичным,
тогда эта ссылка в ответе будет работать