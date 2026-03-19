# Выполненные задачи и этапы

## История выполнения

- [x] Этап 1.1 – Создание структуры директорий – 2026-03-19 – commit pending
  - Созданы директории: backend/, frontend/, data/, tests/ со всеми подпапками
  - Создан requirements.txt с зависимостями FastAPI, SQLAlchemy, JWT, pytest
  - Создан README.md с описанием проекта
  - Создан frontend/package.json с зависимостями React, WGo.js, Vite
  - Созданы __init__.py файлы для всех Python пакетов

- [x] Этап 2.1 – Создание database.py – 2026-03-19 – commit pending
  - Создан backend/database.py с подключением SQLite и сессиями
  - Включен режим WAL для конкурентного доступа
  - Написаны тесты (7 тестов): test_engine_created, test_session_factory, test_wal_mode_enabled, test_init_db, test_reset_db, test_get_db_generator, test_base_class_exists
  - Исправлены ошибки: конфликт версий pydantic, депрекация declarative_base()
