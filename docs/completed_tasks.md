# Выполненные задачи и этапы

## История выполнения

- [x] Этап 1.1 – Создание структуры директорий – 2026-03-19 – commit 2248666
  - Созданы директории: backend/, frontend/, data/, tests/ со всеми подпапками
  - Создан requirements.txt с зависимостями FastAPI, SQLAlchemy, JWT, pytest
  - Создан README.md с описанием проекта
  - Создан frontend/package.json с зависимостями React, WGo.js, Vite
  - Созданы __init__.py файлы для всех Python пакетов

- [x] Этап 2.1 – Создание database.py – 2026-03-19 – commit 2248666
  - Создан backend/database.py с подключением SQLite и сессиями
  - Включен режим WAL для конкурентного доступа
  - Написаны тесты (7 тестов): test_engine_created, test_session_factory, test_wal_mode_enabled, test_init_db, test_reset_db, test_get_db_generator, test_base_class_exists
  - Исправлены ошибки: конфликт версий pydantic, депрекация declarative_base()

- [x] Этап 2.2 – Создание модели User – 2026-03-19 – commit 44fb8b2
  - Создан backend/models/user.py с полями: user_id, user_name, password_hash
  - Написаны тесты (10 тестов): test_create_user, test_user_repr, test_user_unique_username, test_get_user_by_id, test_get_user_by_name, test_delete_user, test_update_user_password, test_user_name_required, test_password_hash_required, test_user_name_max_length
  - Примечание: связь с SolvedTask будет добавлена после создания модели SolvedTask

- [x] Этап 2.3 – Создание модели SolvedTask – 2026-03-19 – commit d6edfd5
  - Создан backend/models/solved_task.py с полями: id, user_id, task_id, sgf_file_name, is_solved, solved_at
  - Добавлена связь relationship в модель User (solved_tasks)
  - Добавлена связь relationship в модель SolvedTask (user)
  - Написаны тесты (20 тестов): test_create_solved_task, test_solved_task_default_values, test_solved_task_repr, test_solved_task_to_dict, test_solved_task_user_relationship, test_user_solved_tasks_relationship, test_cascade_delete_on_user_delete, test_multiple_users_solved_tasks, test_task_id_indexed, test_sgf_file_name_indexed, test_user_id_indexed, test_task_id_max_length, test_sgf_file_name_max_length, test_user_id_required, test_task_id_required, test_sgf_file_name_required, test_get_solved_tasks_by_user, test_get_solved_tasks_by_sgf_file, test_count_solved_tasks_by_user, test_get_solved_tasks_grouped_by_sgf
  - Все тесты пройдены успешно
  - Исправлена депрекация datetime.utcnow() → datetime.now(timezone.utc)

- [x] Этап 2.4 – Тесты моделей (интеграционные) – 2026-03-22
  - Создан tests/test_integration.py с интеграционными тестами для моделей User и SolvedTask
  - Написаны тесты (13 тестов) в 4 категориях:
    - TestUserWithSolvedTasksIntegration (5 тестов): создание пользователя с задачами, прогресс по сборникам, подсчёт задач, пользователь без задач, независимость данных пользователей
    - TestCascadeOperationsIntegration (2 теста): каскадное удаление задач, сохранение задач других пользователей
    - TestComplexQueriesIntegration (3 теста): получение пользователей с количеством задач, популярные сборники, последние решённые задачи
    - TestDataIntegrityIntegration (3 теста): уникальность имени пользователя, уникальность task_id, тест метода to_dict()
  - Все тесты пройдены успешно (13 passed in 3.07s)
  - Обновлён .ai/tests.json с информацией об интеграционных тестах
