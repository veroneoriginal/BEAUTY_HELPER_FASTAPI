# main.py
# Точка входа в приложение.

from fastapi import FastAPI

app = FastAPI(
    title="Beauty Helper API",
    description="Асинхронное API для анализа состава косметических средств",
    version="0.1.0",
)


@app.get("/health")
async def health_check():
    """
    Проверка, что сервер работает.
    """
    return {"status": "ok"}
