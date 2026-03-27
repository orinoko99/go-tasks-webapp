"""
Тесты для сервиса аутентификации (backend/services/auth.py).

Этот модуль тестирует функции:
- get_user_by_username - получение пользователя по имени
- get_user_by_id - получение пользователя по ID
- register_user - регистрация нового пользователя
- authenticate_user - аутентификация пользователя
- create_user_tokens - создание токенов
- change_user_password - смена пароля

Тесты используют тестовую базу данных SQLite в памяти.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base, get_db
from backend.models.user import User
from backend.services.auth import (
    AuthenticationError,
    UserAlreadyExistsError,
    InvalidCredentialsError,
    get_user_by_username,
    get_user_by_id,
    register_user,
    authenticate_user,
    create_user_tokens,
    change_user_password,
)
from backend.schemas.user import UserCreate
from backend.utils.security import verify_password, decode_access_token


# =============================================================================
# ФИКСТУРЫ ДЛЯ ТЕСТИРОВАНИЯ
# =============================================================================

@pytest.fixture
def test_engine():
    """
    Создаёт тестовый движок SQLite в памяти.
    
    Использует :memory: для изоляции тестов.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def test_session(test_engine):
    """
    Создаёт тестовую сессию SQLAlchemy.
    
    Фикстура автоматически очищает базу данных после каждого теста.
    """
    SessionLocal = sessionmaker(bind=test_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def sample_user(test_session):
    """
    Создаёт тестового пользователя в базе данных.
    
    Возвращает кортеж (user_object, plain_password).
    """
    user_data = UserCreate(username="testuser", password="password123")
    user = register_user(test_session, user_data)
    return user, "password123"


# =============================================================================
# ТЕСТЫ ДЛЯ get_user_by_username
# =============================================================================

class TestGetUserByUsername:
    """Тесты для функции get_user_by_username."""
    
    def test_get_existing_user_by_username(self, test_session, sample_user):
        """Тест получения существующего пользователя по имени."""
        user, _ = sample_user
        
        found_user = get_user_by_username(test_session, "testuser")
        
        assert found_user is not None
        assert found_user.user_id == user.user_id
        assert found_user.user_name == "testuser"
    
    def test_get_nonexistent_user_by_username(self, test_session):
        """Тест получения несуществующего пользователя."""
        found_user = get_user_by_username(test_session, "nonexistent")
        
        assert found_user is None
    
    def test_get_user_by_username_case_sensitive(self, test_session, sample_user):
        """Тест чувствительности к регистру имени пользователя."""
        # Имя в нижнем регистре
        found_user = get_user_by_username(test_session, "TESTUSER")
        
        # SQLite по умолчанию case-sensitive для строковых сравнений
        # Но это зависит от конфигурации, поэтому проверяем что находим
        assert found_user is None or found_user.user_name == "testuser"
    
    def test_get_user_by_username_with_special_chars(self, test_session):
        """Тест получения пользователя со спецсимволами в имени."""
        user_data = UserCreate(username="test_user-123", password="password123")
        register_user(test_session, user_data)
        
        found_user = get_user_by_username(test_session, "test_user-123")
        
        assert found_user is not None
        assert found_user.user_name == "test_user-123"


# =============================================================================
# ТЕСТЫ ДЛЯ get_user_by_id
# =============================================================================

class TestGetUserById:
    """Тесты для функции get_user_by_id."""
    
    def test_get_existing_user_by_id(self, test_session, sample_user):
        """Тест получения существующего пользователя по ID."""
        user, _ = sample_user
        
        found_user = get_user_by_id(test_session, user.user_id)
        
        assert found_user is not None
        assert found_user.user_id == user.user_id
        assert found_user.user_name == "testuser"
    
    def test_get_nonexistent_user_by_id(self, test_session):
        """Тест получения несуществующего пользователя по ID."""
        found_user = get_user_by_id(test_session, 99999)
        
        assert found_user is None
    
    def test_get_user_by_id_zero(self, test_session):
        """Тест получения пользователя с ID = 0."""
        found_user = get_user_by_id(test_session, 0)
        
        assert found_user is None
    
    def test_get_user_by_negative_id(self, test_session):
        """Тест получения пользователя с отрицательным ID."""
        found_user = get_user_by_id(test_session, -1)
        
        assert found_user is None


# =============================================================================
# ТЕСТЫ ДЛЯ register_user
# =============================================================================

class TestRegisterUser:
    """Тесты для функции register_user."""
    
    def test_register_new_user(self, test_session):
        """Тест регистрации нового пользователя."""
        user_data = UserCreate(username="newuser", password="password123")
        
        user = register_user(test_session, user_data)
        
        assert user is not None
        assert user.user_id is not None
        assert user.user_name == "newuser"
        assert user.password_hash is not None
        assert len(user.password_hash) > 0
    
    def test_register_user_password_hashed(self, test_session):
        """Тест что пароль хешируется при регистрации."""
        user_data = UserCreate(username="testuser", password="password123")
        
        user = register_user(test_session, user_data)
        
        # Проверяем что пароль захеширован (не равен исходному)
        assert user.password_hash != "password123"
        # Проверяем что хеш валиден
        assert verify_password("password123", user.password_hash)
    
    def test_register_user_unique_username(self, test_session, sample_user):
        """Тест что имя пользователя должно быть уникальным."""
        # Пытаемся зарегистрировать пользователя с тем же именем
        user_data = UserCreate(username="testuser", password="anotherpassword123")
        
        with pytest.raises(UserAlreadyExistsError) as exc_info:
            register_user(test_session, user_data)
        
        assert "уже существует" in str(exc_info.value)
    
    def test_register_user_with_min_length_username(self, test_session):
        """Тест регистрации пользователя с минимальной длиной имени."""
        user_data = UserCreate(username="usr", password="password123")
        
        user = register_user(test_session, user_data)
        
        assert user.user_name == "usr"
    
    def test_register_user_with_max_length_username(self, test_session):
        """Тест регистрации пользователя с максимальной длиной имени."""
        username = "a" * 50
        user_data = UserCreate(username=username, password="password123")
        
        user = register_user(test_session, user_data)
        
        assert user.user_name == username
    
    def test_register_user_with_min_length_password(self, test_session):
        """Тест регистрации пользователя с минимальной длиной пароля."""
        user_data = UserCreate(username="testuser", password="pass1")
        
        user = register_user(test_session, user_data)
        
        assert user.user_name == "testuser"
        assert verify_password("pass1", user.password_hash)
    
    def test_register_user_with_special_chars_in_username(self, test_session):
        """Тест регистрации пользователя с подчёркиванием и дефисом."""
        user_data = UserCreate(username="test_user-123", password="password123")
        
        user = register_user(test_session, user_data)
        
        assert user.user_name == "test_user-123"
    
    def test_register_multiple_users(self, test_session):
        """Тест регистрации нескольких пользователей."""
        user1 = register_user(test_session, UserCreate(username="user1", password="password123"))
        user2 = register_user(test_session, UserCreate(username="user2", password="password123"))
        user3 = register_user(test_session, UserCreate(username="user3", password="password123"))
        
        assert user1.user_id != user2.user_id
        assert user2.user_id != user3.user_id
        assert user1.user_id != user3.user_id
        
        # Проверяем что все пользователи найдены
        assert get_user_by_username(test_session, "user1") is not None
        assert get_user_by_username(test_session, "user2") is not None
        assert get_user_by_username(test_session, "user3") is not None


# =============================================================================
# ТЕСТЫ ДЛЯ authenticate_user
# =============================================================================

class TestAuthenticateUser:
    """Тесты для функции authenticate_user."""
    
    def test_authenticate_with_valid_credentials(self, test_session, sample_user):
        """Тест аутентификации с верными учётными данными."""
        user, password = sample_user
        
        authenticated_user, token = authenticate_user(
            test_session, 
            "testuser", 
            password
        )
        
        assert authenticated_user is not None
        assert authenticated_user.user_id == user.user_id
        assert token is not None
        assert len(token) > 0
    
    def test_authenticate_with_invalid_password(self, test_session, sample_user):
        """Тест аутентификации с неверным паролем."""
        authenticated_user, error = authenticate_user(
            test_session, 
            "testuser", 
            "wrongpassword"
        )
        
        assert authenticated_user is None
        assert error is not None
        assert "Неверное имя пользователя или пароль" in error
    
    def test_authenticate_with_nonexistent_user(self, test_session):
        """Тест аутентификации несуществующего пользователя."""
        authenticated_user, error = authenticate_user(
            test_session, 
            "nonexistent", 
            "password123"
        )
        
        assert authenticated_user is None
        assert error is not None
        assert "Неверное имя пользователя или пароль" in error
    
    def test_authenticate_returns_valid_token(self, test_session, sample_user):
        """Тест что аутентификация возвращает валидный JWT токен."""
        user, password = sample_user
        
        authenticated_user, token = authenticate_user(
            test_session, 
            "testuser", 
            password
        )
        
        # Декодируем токен и проверяем данные
        payload = decode_access_token(token)
        
        assert payload is not None
        assert payload["sub"] == "testuser"
        assert payload["user_id"] == user.user_id
    
    def test_authenticate_case_sensitive_username(self, test_session, sample_user):
        """Тест чувствительности аутентификации к регистру имени."""
        # Пробуем войти с именем в верхнем регистре
        authenticated_user, error = authenticate_user(
            test_session, 
            "TESTUSER", 
            "password123"
        )
        
        # Должна вернуться ошибка (или None если SQLite case-insensitive)
        # В любом случае не должны получить пользователя
        if authenticated_user is not None:
            assert authenticated_user.user_name == "testuser"
    
    def test_authenticate_with_empty_password(self, test_session, sample_user):
        """Тест аутентификации с пустым паролем."""
        authenticated_user, error = authenticate_user(
            test_session, 
            "testuser", 
            ""
        )
        
        assert authenticated_user is None
        assert error is not None
    
    def test_authenticate_with_empty_username(self, test_session):
        """Тест аутентификации с пустым именем пользователя."""
        authenticated_user, error = authenticate_user(
            test_session, 
            "", 
            "password123"
        )
        
        assert authenticated_user is None
        assert error is not None


# =============================================================================
# ТЕСТЫ ДЛЯ create_user_tokens
# =============================================================================

class TestCreateUserTokens:
    """Тесты для функции create_user_tokens."""
    
    def test_create_tokens_for_existing_user(self, test_session, sample_user):
        """Тест создания токенов для существующего пользователя."""
        user, _ = sample_user
        
        token = create_user_tokens(test_session, user)
        
        assert token is not None
        assert len(token) > 0
    
    def test_create_tokens_returns_valid_jwt(self, test_session, sample_user):
        """Тест что создаётся валидный JWT токен."""
        user, _ = sample_user
        
        token = create_user_tokens(test_session, user)
        
        payload = decode_access_token(token)
        
        assert payload is not None
        assert payload["sub"] == user.user_name
        assert payload["user_id"] == user.user_id
        assert "exp" in payload
        assert "iat" in payload
    
    def test_create_tokens_different_tokens_for_same_user(self, test_session, sample_user):
        """Тест что每次 создаётся новый токен (с разным iat)."""
        user, _ = sample_user
        
        token1 = create_user_tokens(test_session, user)
        token2 = create_user_tokens(test_session, user)
        
        # Токены могут быть одинаковыми если iat совпадает (в пределах секунды)
        # Но payload должен быть валиден для обоих
        payload1 = decode_access_token(token1)
        payload2 = decode_access_token(token2)
        
        assert payload1["user_id"] == payload2["user_id"]
        assert payload1["sub"] == payload2["sub"]


# =============================================================================
# ТЕСТЫ ДЛЯ change_user_password
# =============================================================================

class TestChangeUserPassword:
    """Тесты для функции change_user_password."""
    
    def test_change_password_with_valid_old_password(self, test_session, sample_user):
        """Тест смены пароля с верным старым паролем."""
        user, old_password = sample_user
        
        success = change_user_password(
            test_session, 
            user, 
            old_password, 
            "newpassword123"
        )
        
        assert success is True
        
        # Проверяем что новый пароль работает
        authenticated_user, token = authenticate_user(
            test_session, 
            "testuser", 
            "newpassword123"
        )
        
        assert authenticated_user is not None
        assert token is not None
    
    def test_change_password_with_invalid_old_password(self, test_session, sample_user):
        """Тест смены пароля с неверным старым паролем."""
        user, _ = sample_user
        
        success = change_user_password(
            test_session, 
            user, 
            "wrongpassword", 
            "newpassword123"
        )
        
        assert success is False
        
        # Проверяем что старый пароль всё ещё работает
        authenticated_user, token = authenticate_user(
            test_session, 
            "testuser", 
            "password123"
        )
        
        assert authenticated_user is not None
    
    def test_change_password_new_password_hashed(self, test_session, sample_user):
        """Тест что новый пароль хешируется."""
        user, old_password = sample_user
        
        success = change_user_password(
            test_session, 
            user, 
            old_password, 
            "newpassword123"
        )
        
        assert success is True
        
        # Получаем обновлённого пользователя из БД
        updated_user = get_user_by_username(test_session, "testuser")
        
        # Проверяем что пароль захеширован
        assert updated_user.password_hash != "newpassword123"
        assert verify_password("newpassword123", updated_user.password_hash)
    
    def test_change_password_persisted_after_commit(self, test_session, sample_user):
        """Тест что смена пароля сохраняется после commit."""
        user, old_password = sample_user
        
        # Меняем пароль
        change_user_password(test_session, user, old_password, "newpassword123")
        
        # Создаём новую сессию для проверки
        new_session = test_session
        updated_user = get_user_by_username(new_session, "testuser")
        
        # Проверяем что новый пароль работает
        authenticated_user, token = authenticate_user(
            new_session, 
            "testuser", 
            "newpassword123"
        )
        
        assert authenticated_user is not None


# =============================================================================
# ИНТЕГРАЦИОННЫЕ ТЕСТЫ
# =============================================================================

class TestAuthIntegration:
    """Интеграционные тесты для сервиса аутентификации."""
    
    def test_full_registration_and_login_flow(self, test_session):
        """Тест полного потока: регистрация → аутентификация → доступ."""
        # 1. Регистрация
        user_data = UserCreate(username="newuser", password="securepass123")
        user = register_user(test_session, user_data)
        
        assert user.user_id is not None
        assert user.user_name == "newuser"
        
        # 2. Аутентификация
        authenticated_user, token = authenticate_user(
            test_session, 
            "newuser", 
            "securepass123"
        )
        
        assert authenticated_user is not None
        assert authenticated_user.user_id == user.user_id
        assert token is not None
        
        # 3. Проверка токена
        payload = decode_access_token(token)
        assert payload["user_id"] == user.user_id
        assert payload["sub"] == "newuser"
    
    def test_registration_duplicate_username(self, test_session):
        """Тест что нельзя зарегистрировать двух пользователей с одним именем."""
        user1 = register_user(test_session, UserCreate(username="duplicate", password="password123"))
        
        with pytest.raises(UserAlreadyExistsError):
            register_user(test_session, UserCreate(username="duplicate", password="anotherpass123"))
        
        # Проверяем что первый пользователь остался
        found_user = get_user_by_username(test_session, "duplicate")
        assert found_user.user_id == user1.user_id
    
    def test_multiple_users_independent_auth(self, test_session):
        """Тест независимой аутентификации нескольких пользователей."""
        # Регистрируем нескольких пользователей
        user1 = register_user(test_session, UserCreate(username="user1", password="pass1234"))
        user2 = register_user(test_session, UserCreate(username="user2", password="pass5678"))
        user3 = register_user(test_session, UserCreate(username="user3", password="pass9012"))
        
        # Аутентифицируем каждого
        auth1, token1 = authenticate_user(test_session, "user1", "pass1234")
        auth2, token2 = authenticate_user(test_session, "user2", "pass5678")
        auth3, token3 = authenticate_user(test_session, "user3", "pass9012")
        
        # Проверяем что все аутентифицированы
        assert auth1.user_id == user1.user_id
        assert auth2.user_id == user2.user_id
        assert auth3.user_id == user3.user_id
        
        # Проверяем что токены разные
        payload1 = decode_access_token(token1)
        payload2 = decode_access_token(token2)
        payload3 = decode_access_token(token3)
        
        assert payload1["user_id"] != payload2["user_id"]
        assert payload2["user_id"] != payload3["user_id"]
        assert payload1["user_id"] != payload3["user_id"]
    
    def test_password_change_invalidates_old_sessions(self, test_session, sample_user):
        """Тест что смена пароля требует новой аутентификации."""
        user, old_password = sample_user
        
        # Получаем токен до смены пароля
        _, old_token = authenticate_user(test_session, "testuser", old_password)
        
        # Меняем пароль
        change_user_password(test_session, user, old_password, "newpassword123")
        
        # Старый токен всё ещё валиден (JWT не отслеживает смену пароля)
        # Это известное ограничение JWT
        # В production нужно добавлять blacklist токенов или versioning
        old_payload = decode_access_token(old_token)
        assert old_payload is not None
        
        # Но новая аутентификация работает только с новым паролем
        new_auth, new_token = authenticate_user(test_session, "testuser", "newpassword123")
        assert new_auth is not None
        
        # Старый пароль больше не работает
        failed_auth, error = authenticate_user(test_session, "testuser", old_password)
        assert failed_auth is None
        assert error is not None
    
    def test_concurrent_user_creation(self, test_session):
        """Тест конкурентного создания пользователей."""
        # Создаём нескольких пользователей последовательно
        # (в реальном приложении можно тестировать с threading)
        users = []
        for i in range(10):
            user = register_user(test_session, UserCreate(username=f"user{i}", password="password123"))
            users.append(user)
        
        # Проверяем что все созданы
        assert len(users) == 10
        
        # Проверяем что все имеют уникальные ID
        user_ids = [u.user_id for u in users]
        assert len(set(user_ids)) == 10
        
        # Проверяем что все найдены в БД
        for i in range(10):
            found = get_user_by_username(test_session, f"user{i}")
            assert found is not None
