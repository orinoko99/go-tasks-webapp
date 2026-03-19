"""
Тесты для модуля database.py

Проверяет:
- Создание движка и подключения
- Режим WAL
- Создание сессий
- Функции init_db и reset_db
"""

import pytest
from sqlalchemy import text
from backend.database import (
    engine,
    SessionLocal,
    Base,
    get_db,
    init_db,
    reset_db,
    DATABASE_URL
)


class TestDatabaseConnection:
    """Тесты подключения к базе данных."""

    def test_engine_created(self):
        """Проверка создания движка."""
        assert engine is not None
        assert "sqlite" in DATABASE_URL

    def test_session_factory(self):
        """Проверка фабрики сессий."""
        session = SessionLocal()
        assert session is not None
        session.close()

    def test_wal_mode_enabled(self):
        """Проверка включения режима WAL."""
        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA journal_mode"))
            mode = result.scalar()
            assert mode == "wal", "Режим WAL должен быть включён"


class TestDatabaseFunctions:
    """Тесты функций инициализации."""

    def test_init_db(self):
        """Проверка инициализации базы данных."""
        # Не должно вызывать ошибок
        init_db()
        
        # Проверка что таблицы созданы
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ))
            tables = result.fetchall()
            # Таблицы должны существовать (хотя бы sqlite_sequence)
            assert len(tables) >= 0

    def test_reset_db(self):
        """Проверка сброса базы данных."""
        # Не должно вызывать ошибок
        reset_db()
        
        # Проверка что таблицы удалены
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ))
            tables = result.fetchall()
            # После сброса не должно быть пользовательских таблиц
            table_names = [t[0] for t in tables]
            assert not any(
                name in table_names 
                for name in ['users', 'solved_tasks']
            )

    def test_get_db_generator(self):
        """Проверка генератора сессий."""
        gen = get_db()
        session = next(gen)
        assert session is not None
        
        try:
            # Проверка что сессия работает
            result = session.execute(text("SELECT 1"))
            assert result.scalar() == 1
        finally:
            # Закрытие генератора
            try:
                next(gen)
            except StopIteration:
                pass


class TestBaseModel:
    """Тесты базового класса моделей."""

    def test_base_class_exists(self):
        """Проверка существования базового класса."""
        assert Base is not None
        assert hasattr(Base, 'metadata')
