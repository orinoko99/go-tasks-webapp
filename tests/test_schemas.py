"""
Тесты для Pydantic схем пользователей и аутентификации.

Этот модуль тестирует корректность валидации данных в схемах:
- UserCreate - схема регистрации
- UserLogin - схема входа
- UserResponse - схема ответа с данными пользователя
- TokenResponse - схема ответа с токеном
- TokenData - схема данных токена

Тесты проверяют:
- Корректную валидацию правильных данных
- Отклонение некорректных данных
- Работу кастомных валидаторов
- Сериализацию и десериализацию данных
"""

import pytest
from datetime import datetime, timedelta
from pydantic import ValidationError

from backend.schemas.user import (
    UserCreate,
    UserLogin,
    UserResponse,
    TokenResponse,
    TokenData,
)


# =============================================================================
# Тесты для схемы UserCreate
# =============================================================================

class TestUserCreate:
    """Тесты для схемы регистрации пользователя."""
    
    def test_create_user_with_valid_data(self):
        """Тест создания пользователя с корректными данными."""
        user = UserCreate(username="testuser", password="password123")
        
        assert user.username == "testuser"
        assert user.password == "password123"
    
    def test_create_user_with_min_length_username(self):
        """Тест создания пользователя с минимальной длиной имени (3 символа)."""
        user = UserCreate(username="usr", password="password123")
        assert user.username == "usr"
    
    def test_create_user_with_max_length_username(self):
        """Тест создания пользователя с максимальной длиной имени (50 символов)."""
        username = "a" * 50
        user = UserCreate(username=username, password="password123")
        assert user.username == username
    
    def test_create_user_with_min_length_password(self):
        """Тест создания пользователя с минимальной длиной пароля (5 символов)."""
        user = UserCreate(username="testuser", password="pass1")
        assert user.password == "pass1"
    
    def test_create_user_with_max_length_password(self):
        """Тест создания пользователя с максимальной длиной пароля (72 символа)."""
        password = "a" * 71 + "1"  # 71 'a' + 1 цифра = 72 символа
        user = UserCreate(username="testuser", password=password)
        assert user.password == password
    
    def test_username_too_short(self):
        """Тест отклонения имени короче 3 символов."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(username="us", password="password123")
        
        assert "username" in str(exc_info.value)
    
    def test_username_too_long(self):
        """Тест отклонения имени длиннее 50 символов."""
        username = "a" * 51
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(username=username, password="password123")
        
        assert "username" in str(exc_info.value)
    
    def test_password_too_short(self):
        """Тест отклонения пароля короче 5 символов."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(username="testuser", password="pas1")
        
        assert "password" in str(exc_info.value)
    
    def test_password_too_long(self):
        """Тест отклонения пароля длиннее 72 символов."""
        password = "a" * 73
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(username="testuser", password=password)
        
        assert "password" in str(exc_info.value)
    
    def test_username_with_special_characters(self):
        """Тест отклонения имени со спецсимволами."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(username="test@user", password="password123")
        
        assert "username" in str(exc_info.value)
    
    def test_username_with_spaces(self):
        """Тест отклонения имени с пробелами."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(username="test user", password="password123")
        
        assert "username" in str(exc_info.value)
    
    def test_username_empty(self):
        """Тест отклонения пустого имени."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(username="", password="password123")
        
        assert "username" in str(exc_info.value)
    
    def test_username_whitespace_only(self):
        """Тест отклонения имени состоящего только из пробелов."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(username="   ", password="password123")
        
        assert "username" in str(exc_info.value)
    
    def test_username_with_underscore(self):
        """Тест создания пользователя с подчёркиванием в имени."""
        user = UserCreate(username="test_user", password="password123")
        assert user.username == "test_user"
    
    def test_username_with_dash(self):
        """Тест создания пользователя с дефисом в имени."""
        user = UserCreate(username="test-user", password="password123")
        assert user.username == "test-user"
    
    def test_username_with_numbers(self):
        """Тест создания пользователя с цифрами в имени."""
        user = UserCreate(username="user123", password="password123")
        assert user.username == "user123"
    
    def test_password_without_letter(self):
        """Тест отклонения пароля без букв."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(username="testuser", password="123456")
        
        assert "password" in str(exc_info.value)
        assert "букву" in str(exc_info.value)
    
    def test_password_without_digit(self):
        """Тест отклонения пароля без цифр."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(username="testuser", password="password")
        
        assert "password" in str(exc_info.value)
        assert "цифру" in str(exc_info.value)
    
    def test_username_trimmed(self):
        """Тест обрезки пробелов в имени пользователя."""
        user = UserCreate(username="  testuser  ", password="password123")
        assert user.username == "testuser"
    
    def test_password_with_mixed_case(self):
        """Тест создания пользователя с паролем в смешанном регистре."""
        user = UserCreate(username="testuser", password="PaSsWoRd123")
        assert user.password == "PaSsWoRd123"


# =============================================================================
# Тесты для схемы UserLogin
# =============================================================================

class TestUserLogin:
    """Тесты для схемы входа пользователя."""
    
    def test_login_with_valid_data(self):
        """Тест входа с корректными данными."""
        login = UserLogin(username="testuser", password="password123")
        
        assert login.username == "testuser"
        assert login.password == "password123"
    
    def test_login_with_min_length_username(self):
        """Тест входа с именем из 1 символа."""
        login = UserLogin(username="a", password="password123")
        assert login.username == "a"
    
    def test_login_with_max_length_username(self):
        """Тест входа с именем максимальной длины (50 символов)."""
        username = "a" * 50
        login = UserLogin(username=username, password="password123")
        assert login.username == username
    
    def test_login_username_empty(self):
        """Тест отклонения пустого имени при входе."""
        with pytest.raises(ValidationError) as exc_info:
            UserLogin(username="", password="password123")
        
        assert "username" in str(exc_info.value)
    
    def test_login_username_whitespace_only(self):
        """Тест отклонения имени из пробелов при входе."""
        with pytest.raises(ValidationError) as exc_info:
            UserLogin(username="   ", password="password123")
        
        assert "username" in str(exc_info.value)
    
    def test_login_username_trimmed(self):
        """Тест обрезки пробелов в имени при входе."""
        login = UserLogin(username="  testuser  ", password="password123")
        assert login.username == "testuser"
    
    def test_login_password_empty(self):
        """Тест отклонения пустого пароля при входе."""
        with pytest.raises(ValidationError) as exc_info:
            UserLogin(username="testuser", password="")
        
        assert "password" in str(exc_info.value)
    
    def test_login_with_special_characters_in_password(self):
        """Тест входа с паролем содержащим спецсимволы."""
        login = UserLogin(username="testuser", password="p@$$w0rd!123")
        assert login.password == "p@$$w0rd!123"


# =============================================================================
# Тесты для схемы UserResponse
# =============================================================================

class TestUserResponse:
    """Тесты для схемы ответа с данными пользователя."""
    
    def test_user_response_with_valid_data(self):
        """Тест создания ответа с корректными данными."""
        response = UserResponse(user_id=1, username="testuser")
        
        assert response.user_id == 1
        assert response.username == "testuser"
    
    def test_user_response_from_dict(self):
        """Тест создания ответа из словаря."""
        data = {"user_id": 42, "username": "john_doe"}
        response = UserResponse(**data)
        
        assert response.user_id == 42
        assert response.username == "john_doe"
    
    def test_user_response_negative_id(self):
        """Тест создания ответа с отрицательным ID."""
        response = UserResponse(user_id=-1, username="testuser")
        assert response.user_id == -1
    
    def test_user_response_zero_id(self):
        """Тест создания ответа с нулевым ID."""
        response = UserResponse(user_id=0, username="testuser")
        assert response.user_id == 0
    
    def test_user_response_large_id(self):
        """Тест создания ответа с большим ID."""
        response = UserResponse(user_id=999999999, username="testuser")
        assert response.user_id == 999999999
    
    def test_user_response_missing_user_id(self):
        """Тест отклонения ответа без user_id."""
        with pytest.raises(ValidationError) as exc_info:
            UserResponse(username="testuser")
        
        assert "user_id" in str(exc_info.value)
    
    def test_user_response_missing_username(self):
        """Тест отклонения ответа без username."""
        with pytest.raises(ValidationError) as exc_info:
            UserResponse(user_id=1)
        
        assert "username" in str(exc_info.value)


# =============================================================================
# Тесты для схемы TokenResponse
# =============================================================================

class TestTokenResponse:
    """Тесты для схемы ответа с JWT токеном."""
    
    def test_token_response_with_valid_data(self):
        """Тест создания ответа с токеном."""
        response = TokenResponse(access_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9")
        
        assert response.access_token == "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        assert response.token_type == "bearer"
    
    def test_token_response_with_custom_token_type(self):
        """Тест создания ответа с кастомным типом токена."""
        response = TokenResponse(
            access_token="test_token",
            token_type="custom"
        )
        
        assert response.access_token == "test_token"
        assert response.token_type == "custom"
    
    def test_token_response_missing_token(self):
        """Тест отклонения ответа без токена."""
        with pytest.raises(ValidationError) as exc_info:
            TokenResponse()
        
        assert "access_token" in str(exc_info.value)
    
    def test_token_response_default_token_type(self):
        """Тест значения по умолчанию для token_type."""
        response = TokenResponse(access_token="test_token")
        assert response.token_type == "bearer"


# =============================================================================
# Тесты для схемы TokenData
# =============================================================================

class TestTokenData:
    """Тесты для схемы данных JWT токена."""
    
    def test_token_data_with_valid_data(self):
        """Тест создания данных токена с корректными значениями."""
        now = datetime.now()
        exp = now + timedelta(hours=1)
        
        data = TokenData(
            user_id=1,
            username="testuser",
            exp=exp,
            iat=now
        )
        
        assert data.user_id == 1
        assert data.username == "testuser"
        assert data.exp == exp
        assert data.iat == now
    
    def test_token_data_missing_exp(self):
        """Тест отклонения данных токена без времени истечения."""
        now = datetime.now()
        
        with pytest.raises(ValidationError) as exc_info:
            TokenData(
                user_id=1,
                username="testuser",
                iat=now
            )
        
        assert "exp" in str(exc_info.value)
    
    def test_token_data_missing_iat(self):
        """Тест отклонения данных токена без времени создания."""
        now = datetime.now()
        
        with pytest.raises(ValidationError) as exc_info:
            TokenData(
                user_id=1,
                username="testuser",
                exp=now
            )
        
        assert "iat" in str(exc_info.value)
    
    def test_token_data_missing_user_id(self):
        """Тест отклонения данных токена без user_id."""
        now = datetime.now()
        
        with pytest.raises(ValidationError) as exc_info:
            TokenData(
                username="testuser",
                exp=now,
                iat=now
            )
        
        assert "user_id" in str(exc_info.value)
    
    def test_token_data_missing_username(self):
        """Тест отклонения данных токена без username."""
        now = datetime.now()
        
        with pytest.raises(ValidationError) as exc_info:
            TokenData(
                user_id=1,
                exp=now,
                iat=now
            )
        
        assert "username" in str(exc_info.value)


# =============================================================================
# Интеграционные тесты схем
# =============================================================================

class TestSchemasIntegration:
    """Интеграционные тесты для схем."""
    
    def test_user_create_to_user_response_flow(self):
        """Тест потока от создания пользователя к ответу."""
        # Создаём данные для регистрации
        user_create = UserCreate(username="newuser", password="password123")
        
        # Имитируем создание пользователя в БД и получение ответа
        user_response = UserResponse(user_id=1, username=user_create.username)
        
        assert user_response.username == user_create.username
        assert user_response.user_id == 1
    
    def test_login_to_token_response_flow(self):
        """Тест потока от входа к получению токена."""
        # Создаём данные для входа
        login = UserLogin(username="testuser", password="password123")
        
        # Имитируем успешный вход и получение токена
        token_response = TokenResponse(access_token="fake_jwt_token")
        
        assert login.username == "testuser"
        assert token_response.access_token == "fake_jwt_token"
        assert token_response.token_type == "bearer"
    
    def test_model_dump_and_parse(self):
        """Тест сериализации и десериализации схем."""
        # Создаём схему
        user = UserCreate(username="testuser", password="password123")
        
        # Сериализуем в dict
        data = user.model_dump()
        assert data == {"username": "testuser", "password": "password123"}
        
        # Десериализуем обратно
        user2 = UserCreate(**data)
        assert user2.username == user.username
        assert user2.password == user.password
    
    def test_model_dump_json(self):
        """Тест JSON сериализации."""
        user = UserCreate(username="testuser", password="password123")
        
        # Сериализуем в JSON
        json_data = user.model_dump_json()
        
        assert "testuser" in json_data
        assert "password123" in json_data
