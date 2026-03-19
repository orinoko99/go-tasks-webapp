# Описание Тестов

## Примеры Unit Тестов (pytest для backend, jest для frontend)
- Тест auth: Регистрация, логин, invalid creds.
- Тест задач: Парсинг SGF, отметка solved.
- Тест concurrency: Симулировать 10 одновременных запросов (с threading).

## Примеры E2E Тестов (cypress)
- Сквозной тест: Логин -> Выбор задачи -> Решение -> Проверка в БД.

## Инструкции для AI
- Генерируй тесты в tests/.
- Запусти: `pytest` или `npm test`.
- Результаты: В error_log.md.
- используй pytest для backend, jest для frontend