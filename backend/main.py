"""
Точка входа FastAPI приложения Go Problems Trainer.

Этот модуль инициализирует FastAPI приложение, подключает маршруты,
настраивает CORS и предоставляет endpoints для проверки работоспособности.

Основное приложение:
- Создаёт экземпляр FastAPI с метаданными
- Подключает роутеры (auth, tasks, etc.)
- Настраивает CORS для frontend
- Предоставляет health check endpoint

Запуск сервера:
    uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

Для разработки с автоперезагрузкой:
    uvicorn backend.main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routes.auth import router as auth_router


# =============================================================================
# КОНФИГУРАЦИЯ ПРИЛОЖЕНИЯ
# =============================================================================

# Создаём экземпляр FastAPI с метаданными для документации
# Эти данные отображаются в /docs (Swagger UI) и /redoc (ReDoc)
app = FastAPI(
    title="Go Problems Trainer API",
    description=(
        "REST API для веб-приложения решения задач по игре Go (Baduk).\n\n"
        "Функционал:\n"
        "- Аутентификация и регистрация пользователей\n"
        "- Управление сборниками задач (SGF файлы)\n"
        "- Решение задач с интерактивной доской\n"
        "- Отслеживание прогресса пользователя"
    ),
    version="1.0.0",
    docs_url="/docs",      # Swagger UI доступен по /docs
    redoc_url="/redoc",    # ReDoc доступен по /redoc
    openapi_url="/openapi.json"  # OpenAPI схема доступна по /openapi.json
)


# =============================================================================
# НАСТРОЙКА CORS (Cross-Origin Resource Sharing)
# =============================================================================

# Разрешаем frontend делать запросы к backend с другого домена/порта
# Это необходимо для разделения frontend (React, порт 3000/5173) и backend (FastAPI, порт 8000)
app.add_middleware(
    CORSMiddleware,
    # Разрешаем запросы с frontend (в разработке обычно localhost:3000 или localhost:5173)
    # В продакшене заменить на реальный домен frontend
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    # Разрешаем все методы HTTP (GET, POST, PUT, DELETE, etc.)
    allow_methods=["*"],
    # Разрешаем все заголовки (Authorization, Content-Type, etc.)
    allow_headers=["*"],
    # Разрешаем отправку cookies и credentials
    allow_credentials=True,
)


# =============================================================================
# ПОДКЛЮЧЕНИЕ МАРШРУТОВ (ROUTERS)
# =============================================================================

# Подключаем роутер аутентификации
# Все endpoints из auth_router будут доступны с префиксом /auth
# Например: /auth/register, /auth/login
app.include_router(auth_router)

# В будущем здесь будут подключены другие роутеры:
# app.include_router(tasks_router, prefix="/tasks", tags=["Tasks"])
# app.include_router(collections_router, prefix="/collections", tags=["Collections"])


# =============================================================================
# ENDPOINTS ОБЩЕГО НАЗНАЧЕНИЯ
# =============================================================================

@app.get(
    "/",
    summary="Корневой endpoint",
    description="Возвращает приветственное сообщение и статус API.",
    tags=["Health Check"]
)
def root() -> dict[str, str]:
    """
    Корневой endpoint для проверки работоспособности API.

    Returns:
        dict: Приветственное сообщение со статусом API

    Example:
        GET /

        Response:
        {
            "message": "Go Problems Trainer API",
            "status": "running",
            "docs": "/docs"
        }

    Usage:
        Используется для быстрой проверки, что сервер запущен.
    """
    return {
        "message": "Go Problems Trainer API",
        "status": "running",
        "docs": "/docs"
    }


@app.get(
    "/health",
    summary="Проверка работоспособности",
    description="Health check endpoint для мониторинга состояния API.",
    tags=["Health Check"]
)
def health_check() -> dict[str, str]:
    """
    Endpoint для проверки здоровья приложения.

    Returns:
        dict: Статус здоровья приложения

    Example:
        GET /health

        Response:
        {
            "status": "healthy"
        }

    Usage:
        Используется системами мониторинга (Kubernetes, Prometheus, etc.)
        для проверки доступности приложения.
    """
    return {"status": "healthy"}


# =============================================================================
# ТОЧКА ВХОДА ДЛЯ ЗАПУСКА
# =============================================================================

# Эта конструкция позволяет запускать приложение через:
# python -m backend.main
# или
# uvicorn backend.main:app --reload
if __name__ == "__main__":
    import uvicorn

    # Запускаем сервер разработки uvicorn
    # host="0.0.0.0" - слушать все сетевые интерфейсы
    # port=8000 - порт 8000
    # reload=True - автоперезагрузка при изменении кода (только для разработки)
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True
    )
