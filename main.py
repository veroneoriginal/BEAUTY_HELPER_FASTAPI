# main.py
# Точка входа в приложение.

from fastapi import FastAPI
from apps.auth.routes import router as auth_router

app = FastAPI(
    title="Beauty Helper API",
    description="Асинхронное API для анализа состава косметических средств",
    version="0.1.0",
)

# === Роутеры регистрации и аутентификации ===
app.include_router(auth_router)

@app.get("/health")
async def health_check():
    """
    Проверка, что сервер работает.
    """
    return {"status": "ok"}
