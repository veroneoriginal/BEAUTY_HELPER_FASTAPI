https://goldapple.ru/19000002015-moisture-surge-100h
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
"confirmation_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwidHlwZSI6ImVtYWlsX2NvbmZpcm1hdGlvbiIsImV4cCI6MTc4MDgzMDcwMX0.eUTeclNaK9dMFr5ZzG5pF7OqS8nHy7shb2hjWS3S4II"
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
"access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiZXhwIjoxNzgwNzQ2MjM3LCJ0eXBlIjoiYWNjZXNzIn0.GPFDk2fp8jmu1KGs_g2MYSpp-MnIi96IUefiJq2kHfg",
"refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiZXhwIjoxNzgxMzQ5MjM3LCJ0eXBlIjoicmVmcmVzaCJ9.zL_1_twPrY9vonKYdybS3xApcfiNibxLginrlz-pU8Q",
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