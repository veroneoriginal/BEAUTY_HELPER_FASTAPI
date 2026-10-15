FROM python:3.12-slim

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Зависимости отдельным слоем — кешируется при пересборке
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Chromium для парсера (Playwright) и системные библиотеки к нему
RUN playwright install --with-deps chromium

# Словарь tiktoken для подсчёта токенов — скачиваем при сборке, а не при
# первой генерации (там он падал на DNS). Папка вне /app: /app закрыт томом
# с кодом. o200k_base — словарь gpt-4o-mini; другая модель — пересобрать образ
ENV TIKTOKEN_CACHE_DIR=/opt/tiktoken_cache
RUN python -c "import tiktoken; tiktoken.get_encoding('o200k_base')"

# Код приложения
COPY . .

EXPOSE 8000

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]