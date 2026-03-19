# Roadmap проекта Go Problems Trainer

## Этап 1: Инициализация проекта
- [ ] 1.1 Создать структуру директорий (backend/, frontend/, data/, tests/)
- [ ] 1.2 Создать requirements.txt с зависимостями
- [ ] 1.3 Создать README.md проекта

## Этап 2: Backend — База данных и модели
- [ ] 2.1 Создать database.py (подключение SQLite, сессии)
- [ ] 2.2 Создать модель User (models/user.py)
- [ ] 2.3 Создать модель SolvedTask (models/solved_task.py)
- [ ] 2.4 Тесты: models test

## Этап 3: Backend — Аутентификация
- [ ] 3.1 Создать utils/security.py (хеширование паролей, JWT)
- [ ] 3.2 Создать schemas/user.py (Pydantic схемы)
- [ ] 3.3 Создать services/auth.py (логика auth)
- [ ] 3.4 Создать routes/auth.py (endpoints /register, /login)
- [ ] 3.5 Тесты: test_auth.py (регистрация, логин, невалидные данные)

## Этап 4: Backend — SGF парсер
- [ ] 4.1 Создать services/sgf_parser.py (парсинг SGF файлов)
- [ ] 4.2 Создать services/task_resolver.py (проверка ходов)
- [ ] 4.3 Создать schemas/task.py (схемы для задач)
- [ ] 4.4 Тесты: test_sgf.py (парсинг, координаты, дерево ходов)

## Этап 5: Backend — Задачи (Tasks API)
- [ ] 5.1 Создать routes/tasks.py (endpoints /tasks/list, /tasks/solve/{id})
- [ ] 5.2 Тесты: test_tasks.py (список задач, решение)

## Этап 6: Frontend — Инициализация
- [ ] 6.1 Создать React приложение (package.json, public/index.html)
- [ ] 6.2 Создать main.jsx, App.jsx
- [ ] 6.3 Создать services/api.js (API вызовы)
- [ ] 6.4 Тесты: jest базовые

## Этап 7: Frontend — Компоненты
- [ ] 7.1 Создать Auth.jsx (форма входа/регистрации)
- [ ] 7.2 Создать Board.jsx (доска WGo.js)
- [ ] 7.3 Создать CollectionList.jsx (список сборников)
- [ ] 7.4 Создать TaskList.jsx (список задач)
- [ ] 7.5 Создать Profile.jsx (профиль пользователя)
- [ ] 7.6 Тесты: jest component tests

## Этап 8: Интеграция и тестирование
- [ ] 8.1 E2E тесты (Cypress): логин → задача → решение
- [ ] 8.2 Тесты concurrency
- [ ] 8.3 Финальное тестирование

---

## Current stage
**Этап 1.1** — Создание структуры директорий
