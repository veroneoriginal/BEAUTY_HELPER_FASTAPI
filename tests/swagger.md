## Проверяем, что Analysis не работает без авторизации.
{
"product_link": "https://goldapple.ru/9400200001-bamboo-creme-frappee",
"task_type": "detailed_analysis"
}

### Получаем 401 - {"detail": "Not authenticated"}

## Регистрация пользователя
{
"email": "user_number1@example.com",
"password": "123456n1"
}
### Получаем 201 Response body
{
"message": "Пользователь зарегистрирован. Проверьте почту для подтверждения email.",
"confirmation_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwidHlwZSI6ImVtYWlsX2NvbmZpcm1hdGlvbiIsImV4cCI6MTc4MDA4MjI0Nn0.ABJIqiwSLlssZB1tIO4_61QeDLpcO5G1EEojb-wpZvM"
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
"password": "123456n1"
}

### Получаем 200 Response body
{
"access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiZXhwIjoxNzc5OTk4NDgxfQ.0Bi7xzUne9IE1Ig9PtS1nWcPm43YKV4yBhZdvScuByI",
"refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiZXhwIjoxNzgwNjAxNDgxLCJ0eXBlIjoicmVmcmVzaCJ9.s4m1m9y8nwT0qH3qiekGS9aQSGodZyt-lmrfy3csfB0",
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