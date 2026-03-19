"""
Тесты для модели User.

Проверяет:
- Создание экземпляра User
- Сохранение и загрузка из БД
- Уникальность user_name
- Связь с SolvedTask (будет добавлена позже)
- Представление __repr__
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database import Base, get_db
from backend.models.user import User


# Тестовая база данных в памяти
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db_session():
    """
    Фикстура для создания сессии БД.
    
    Создаёт таблицы перед каждым тестом и удаляет после.
    """
    # Создание таблиц
    Base.metadata.create_all(bind=test_engine)
    
    # Создание сессии
    session = TestingSessionLocal()
    yield session
    
    # Удаление таблиц после теста
    session.close()
    Base.metadata.drop_all(bind=test_engine)


class TestUserCreation:
    """Тесты создания пользователя."""

    def test_create_user(self, db_session):
        """Проверка создания пользователя."""
        user = User(user_name="test_user", password_hash="hashed_password_123")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        assert user.user_id is not None
        assert user.user_name == "test_user"
        assert user.password_hash == "hashed_password_123"

    def test_user_repr(self, db_session):
        """Проверка строкового представления."""
        user = User(user_name="john_doe", password_hash="hash")
        db_session.add(user)
        db_session.commit()
        
        assert repr(user) == "<User john_doe>"

    def test_user_unique_username(self, db_session):
        """Проверка уникальности имени пользователя."""
        user1 = User(user_name="unique_user", password_hash="hash1")
        user2 = User(user_name="unique_user", password_hash="hash2")
        
        db_session.add(user1)
        db_session.commit()
        
        # Попытка добавить пользователя с тем же именем должна вызвать ошибку
        db_session.add(user2)
        with pytest.raises(Exception):
            db_session.commit()
        db_session.rollback()


class TestUserDatabaseOperations:
    """Тесты операций с базой данных."""

    def test_get_user_by_id(self, db_session):
        """Проверка получения пользователя по ID."""
        user = User(user_name="find_by_id", password_hash="hash")
        db_session.add(user)
        db_session.commit()
        user_id = user.user_id
        
        # Получение пользователя
        found_user = db_session.query(User).filter(User.user_id == user_id).first()
        
        assert found_user is not None
        assert found_user.user_name == "find_by_id"

    def test_get_user_by_name(self, db_session):
        """Проверка получения пользователя по имени."""
        user = User(user_name="find_by_name", password_hash="hash")
        db_session.add(user)
        db_session.commit()
        
        # Получение пользователя по имени
        found_user = db_session.query(User).filter(User.user_name == "find_by_name").first()
        
        assert found_user is not None
        assert found_user.user_id == user.user_id

    def test_delete_user(self, db_session):
        """Проверка удаления пользователя."""
        user = User(user_name="to_delete", password_hash="hash")
        db_session.add(user)
        db_session.commit()
        user_id = user.user_id
        
        # Удаление
        db_session.delete(user)
        db_session.commit()
        
        # Проверка что удалён
        deleted_user = db_session.query(User).filter(User.user_id == user_id).first()
        assert deleted_user is None

    def test_update_user_password(self, db_session):
        """Проверка обновления пароля пользователя."""
        user = User(user_name="update_pwd", password_hash="old_hash")
        db_session.add(user)
        db_session.commit()
        
        # Обновление пароля
        user.password_hash = "new_hash"
        db_session.commit()
        
        # Проверка обновления
        updated_user = db_session.query(User).filter(User.user_id == user.user_id).first()
        assert updated_user.password_hash == "new_hash"


class TestUserValidation:
    """Тесты валидации полей."""

    def test_user_name_required(self, db_session):
        """Проверка обязательности имени пользователя."""
        user = User(user_name=None, password_hash="hash")
        
        with pytest.raises(Exception):
            db_session.add(user)
            db_session.commit()

    def test_password_hash_required(self, db_session):
        """Проверка обязательности хэша пароля."""
        user = User(user_name="no_password", password_hash=None)
        
        with pytest.raises(Exception):
            db_session.add(user)
            db_session.commit()

    def test_user_name_max_length(self, db_session):
        """Проверка максимальной длины имени пользователя (50 символов)."""
        # Имя длиной 50 символов должно работать
        long_name = "a" * 50
        user = User(user_name=long_name, password_hash="hash")
        db_session.add(user)
        db_session.commit()
        
        assert user.user_name == long_name
        
        # Примечание: SQLite не ограничивает длину строки на уровне БД
        # Валидация длины будет добавлена на уровне Pydantic схем
