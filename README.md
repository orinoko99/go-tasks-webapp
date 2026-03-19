# Go Problems Trainer - Веб-приложение для решения задач по игре Go

## Описание
Веб-приложение для тренировки и решения задач по игре Go (Baduk). Приложение предоставляет интерактивную доску, коллекцию задач из SGF-файлов и систему отслеживания прогресса пользователей.

## Технологии
- **Backend**: Python, FastAPI
- **Frontend**: React, WGo.js
- **База данных**: SQLite (с возможностью миграции на PostgreSQL)
- **SGF Парсер**: sgfparse

## Функционал
- Регистрация и авторизация пользователей (JWT)
- Просмотр и фильтрация сборников задач
- Интерактивная доска для решения задач
- Проверка ходов и обратная связь
- Отслеживание прогресса и статистики
- Адаптивный дизайн для мобильных устройств

## Структура проекта
```
go-tasks-webapp/
├── backend/          # Backend на FastAPI
├── frontend/         # Frontend на React
├── data/            # Данные (SGF файлы, БД)
├── tests/           # Тесты
└── docs/            # Документация
```

## Установка

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Запуск тестов
```bash
pytest tests/ -v
```

## Лицензия
MIT
