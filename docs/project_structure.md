# Структура проекта Go Problems Trainer

```
go-tasks-webapp/
├── backend/
│   ├── main.py                 # Точка входа FastAPI
│   ├── config.py               # Конфигурация приложения
│   ├── database.py             # Подключение к БД, сессии
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py             # Модель пользователя
│   │   └── solved_task.py      # Модель решённых задач
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── user.py             # Pydantic схемы для пользователя
│   │   └── task.py             # Pydantic схемы для задач
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py             # Auth endpoints (register, login)
│   │   └── tasks.py            # Tasks endpoints (list, solve)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth.py             # Логика аутентификации
│   │   ├── sgf_parser.py       # Парсинг SGF файлов
│   │   └── task_resolver.py    # Логика проверки ходов
│   └── utils/
│       ├── __init__.py
│       └── security.py         # Хэширование паролей, JWT
├── frontend/
│   ├── public/
│   │   └── index.html
│   ├── src/
│   │   ├── App.jsx             # Главный компонент
│   │   ├── main.jsx            # Точка входа React
│   │   ├── components/
│   │   │   ├── Board.jsx       # Компонент доски (WGo.js)
│   │   │   ├── TaskList.jsx    # Список задач
│   │   │   ├── CollectionList.jsx # Список сборников
│   │   │   ├── Auth.jsx        # Форма входа/регистрации
│   │   │   └── Profile.jsx     # Профиль пользователя
│   │   ├── services/
│   │   │   └── api.js          # API вызовы к backend
│   │   └── styles/
│   │       └── App.css
│   └── package.json
├── data/
│   ├── sgf/                    # SGF файлы с задачами
│   └── database.db             # SQLite БД
├── tests/
│   ├── __init__.py
│   ├── test_auth.py            # Тесты аутентификации
│   └── test_sgf.py             # Тесты парсера
├── docs/                       # Документация (уже есть)
├── README.md                   # Описание проекта
└── requirements.txt            # Python зависимости
```
