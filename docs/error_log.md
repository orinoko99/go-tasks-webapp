# Журнал ошибок

## 2026-03-19 15:30
Проблема: Невозможно установить sgfparse==1.1.1 или sgfparse==1.0.0
Файлы: requirements.txt
Воспроизведение: pip install -r requirements.txt
Предлагаемое решение: Использовать альтернативную библиотеку sgf==0.5

## 2026-03-19 15:35
Проблема: Длительная установка зависимостей (компиляция pydantic-core)
Файлы: requirements.txt
Воспроизведение: pip install -r requirements.txt зависает на этапе "Preparing metadata (pyproject.toml)"
Предлагаемое решение: Дождаться завершения установки или использовать предварительно скомпилированные колеса (binary wheels)

## 2026-03-19 15:40
Проблема: Конфликт версий pydantic между sgflib и fastapi
Файлы: requirements.txt
Воспроизведение: sgflib требует pydantic<2.0.0, fastapi требует pydantic>=2.7.0
Решение: Использовать библиотеку sgf==0.5 вместо sgflib

## 2026-03-19 15:45
Проблема: Депрекация declarative_base() в SQLAlchemy 2.0
Файлы: backend/database.py:40
Воспроизведение: pytest выдает предупреждение MovedIn20Warning
Решение: Импортировать declarative_base() из sqlalchemy.orm вместо sqlalchemy.ext.declarative

## 2026-03-19 16:00
Проблема: Циклическая зависимость между User и SolvedTask
Файлы: backend/models/user.py
Воспроизведение: тесты test_user_model.py падают с ошибкой "failed to locate a name SolvedTask"
Решение: Временно убрать relationship из модели User до создания модели SolvedTask (Этап 2.3)
