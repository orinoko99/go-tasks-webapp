"""
Тесты для модуля безопасности backend/utils/security.py.

Этот файл содержит тесты для проверки:
- Хеширования паролей (hash_password)
- Проверки паролей (verify_password)
- Создания JWT токенов (create_access_token)
- Декодирования JWT токенов (decode_access_token)
- Извлечения данных пользователя из токена (get_user_from_token)
- Истечения срока действия токенов
- Обработки невалидных токенов

Запуск тестов:
    pytest tests/test_security.py -v

Покрытие тестами:
    pytest tests/test_security.py --cov=backend.utils.security
"""

import time
from datetime import timedelta

import pytest

from backend.utils.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    JWT_ALGORITHM,
    JWT_SECRET_KEY,
    create_access_token,
    decode_access_token,
    get_user_from_token,
    hash_password,
    verify_password,
)


# =============================================================================
# ТЕСТЫ ХЕШИРОВАНИЯ ПАРОЛЕЙ (hash_password)
# =============================================================================

class TestHashPassword:
    """Тесты для функции хеширования паролей."""

    def test_hash_password_returns_string(self):
        """Тест: hash_password возвращает строку."""
        password = "test_password123"
        hashed = hash_password(password)
        
        assert isinstance(hashed, str), "Хеш должен быть строкой"

    def test_hash_password_returns_different_hashes_for_same_password(self):
        """Тест: одинаковые пароли дают разные хеши из-за случайной соли."""
        password = "same_password"
        
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        # bcrypt генерирует случайную соль для каждого вызова
        # поэтому хеши должны отличаться
        assert hash1 != hash2, "Хеши одного пароля должны отличаться (разная соль)"

    def test_hash_password_returns_different_hashes_for_different_passwords(self):
        """Тест: разные пароли дают разные хеши."""
        hash1 = hash_password("password_one")
        hash2 = hash_password("password_two")
        
        assert hash1 != hash2, "Хеши разных паролей должны отличаться"

    def test_hash_password_handles_empty_password(self):
        """Тест: хеширование пустого пароля."""
        hashed = hash_password("")
        
        assert isinstance(hashed, str), "Хеш пустого пароля должен быть строкой"
        assert len(hashed) > 0, "Хеш не должен быть пустой строкой"

    def test_hash_password_handles_unicode(self):
        """Тест: хеширование паролей с Unicode символами."""
        password = "пароль_密码🔐"
        hashed = hash_password(password)
        
        assert isinstance(hashed, str), "Хеш Unicode пароля должен быть строкой"

    def test_hash_password_handles_long_password(self):
        """Тест: хеширование длинного пароля (обрезается до 72 байт)."""
        # bcrypt поддерживает только 72 байта пароля
        # Пароли длиннее 72 байт обрезаются
        long_password = "a" * 100  # Длинный пароль
        hashed = hash_password(long_password)
        
        assert isinstance(hashed, str), "Хеш длинного пароля должен быть строкой"
        
        # Проверяем что обрезанный пароль работает
        truncated = long_password[:72]
        assert verify_password(truncated, hashed) is True

    def test_hash_password_bcrypt_format(self):
        """Тест: хеш соответствует формату bcrypt ($2b$cost$salt+hash)."""
        password = "test_password"
        hashed = hash_password(password)
        
        # bcrypt хеши начинаются с $2a$, $2b$ или $2y$
        assert hashed.startswith("$2"), f"bcrypt хеш должен начинаться с $2, получен: {hashed}"
        
        # Формат: $version$cost$salt+hash (примерно 60 символов)
        assert len(hashed) >= 60, f"bcrypt хеш должен быть >= 60 символов, получен: {len(hashed)}"


# =============================================================================
# ТЕСТЫ ПРОВЕРКИ ПАРОЛЕЙ (verify_password)
# =============================================================================

class TestVerifyPassword:
    """Тесты для функции проверки паролей."""

    def test_verify_password_correct_password(self):
        """Тест: проверка правильного пароля."""
        password = "correct_password123"
        hashed = hash_password(password)
        
        result = verify_password(password, hashed)
        
        assert result is True, "Правильный пароль должен пройти проверку"

    def test_verify_password_wrong_password(self):
        """Тест: проверка неправильного пароля."""
        hashed = hash_password("original_password")
        
        result = verify_password("wrong_password", hashed)
        
        assert result is False, "Неправильный пароль не должен пройти проверку"

    def test_verify_password_empty_password(self):
        """Тест: проверка пустого пароля."""
        hashed = hash_password("")
        
        # Пустой пароль должен совпадать с самим собой
        result_empty = verify_password("", hashed)
        assert result_empty is True, "Пустой пароль должен совпадать"
        
        # Непустой пароль не должен совпадать с хешем пустого
        result_non_empty = verify_password("not_empty", hashed)
        assert result_non_empty is False, "Непустой пароль не должен совпадать с пустым"

    def test_verify_password_case_sensitive(self):
        """Тест: проверка чувствительности к регистру."""
        password = "Password123"
        hashed = hash_password(password)
        
        # Пароли с разным регистром не должны совпадать
        assert verify_password("Password123", hashed) is True
        assert verify_password("password123", hashed) is False
        assert verify_password("PASSWORD123", hashed) is False
        assert verify_password("PaSsWoRd123", hashed) is False

    def test_verify_password_unicode(self):
        """Тест: проверка паролей с Unicode символами."""
        password = "пароль_密码🔐"
        hashed = hash_password(password)
        
        result = verify_password(password, hashed)
        
        assert result is True, "Unicode пароль должен пройти проверку"

    def test_verify_password_with_whitespace(self):
        """Тест: проверка паролей с пробелами."""
        password_with_space = "password with spaces"
        hashed = hash_password(password_with_space)
        
        # Пароль с пробелами должен совпадать
        assert verify_password("password with spaces", hashed) is True
        
        # Пароль без пробелов не должен совпадать
        assert verify_password("passwordwithspaces", hashed) is False

    def test_verify_password_invalid_hash(self):
        """Тест: проверка с невалидным хешем."""
        # passlib должен корректно обрабатывать невалидные хеши
        result = verify_password("password", "invalid_hash_format")
        
        assert result is False, "Невалидный хеш должен возвращать False"


# =============================================================================
# ТЕСТЫ СОЗДАНИЯ JWT ТОКЕНОВ (create_access_token)
# =============================================================================

class TestCreateAccessToken:
    """Тесты для функции создания JWT токенов."""

    def test_create_access_token_returns_string(self):
        """Тест: create_access_token возвращает строку."""
        token = create_access_token(data={"sub": "test_user"})
        
        assert isinstance(token, str), "Токен должен быть строкой"

    def test_create_access_token_token_format(self):
        """Тест: токен имеет формат JWT (header.payload.signature)."""
        token = create_access_token(data={"sub": "test_user"})
        
        # JWT токен состоит из трёх частей, разделённых точкой
        parts = token.split(".")
        assert len(parts) == 3, f"JWT должен иметь 3 части, получено: {len(parts)}"

    def test_create_access_token_contains_user_data(self):
        """Тест: токен содержит данные пользователя."""
        user_data = {"sub": "john_doe", "user_id": 42, "role": "admin"}
        token = create_access_token(data=user_data)
        
        # Декодируем токен для проверки содержимого
        payload = decode_access_token(token)
        
        assert payload is not None, "Токен должен декодироваться"
        assert payload["sub"] == "john_doe", "Токен должен содержать sub"
        assert payload["user_id"] == 42, "Токен должен содержать user_id"
        assert payload["role"] == "admin", "Токен должен содержать role"

    def test_create_access_token_contains_expiration(self):
        """Тест: токен содержит время истечения (exp)."""
        token = create_access_token(data={"sub": "test_user"})
        
        payload = decode_access_token(token)
        
        assert "exp" in payload, "Токен должен содержать claim exp (время истечения)"
        assert "iat" in payload, "Токен должен содержать claim iat (время создания)"

    def test_create_access_token_default_expiration(self):
        """Тест: токен имеет время жизни по умолчанию 30 минут."""
        token = create_access_token(data={"sub": "test_user"})
        payload = decode_access_token(token)
        
        exp_time = payload["exp"]
        iat_time = payload["iat"]
        
        # Разница между exp и iat должна быть примерно 30 минут (1800 секунд)
        expected_delta = ACCESS_TOKEN_EXPIRE_MINUTES * 60
        actual_delta = exp_time - iat_time
        
        # Допускаем небольшую погрешность (±2 секунды)
        assert abs(actual_delta - expected_delta) <= 2, \
            f"Время жизни токена должно быть {expected_delta} секунд, получено: {actual_delta}"

    def test_create_access_token_custom_expiration(self):
        """Тест: токен с кастомным временем жизни."""
        custom_delta = timedelta(hours=2)  # 2 часа
        token = create_access_token(
            data={"sub": "test_user"},
            expires_delta=custom_delta
        )
        
        payload = decode_access_token(token)
        
        exp_time = payload["exp"]
        iat_time = payload["iat"]
        
        expected_delta = 2 * 60 * 60  # 2 часа в секундах
        actual_delta = exp_time - iat_time
        
        assert abs(actual_delta - expected_delta) <= 2, \
            f"Время жизни токена должно быть {expected_delta} секунд, получено: {actual_delta}"

    def test_create_access_token_short_expiration(self):
        """Тест: токен с коротким временем жизни (5 минут)."""
        custom_delta = timedelta(minutes=5)
        token = create_access_token(
            data={"sub": "test_user"},
            expires_delta=custom_delta
        )
        
        payload = decode_access_token(token)
        
        exp_time = payload["exp"]
        iat_time = payload["iat"]
        
        expected_delta = 5 * 60  # 5 минут в секундах
        actual_delta = exp_time - iat_time
        
        assert abs(actual_delta - expected_delta) <= 2, \
            f"Время жизни токена должно быть {expected_delta} секунд, получено: {actual_delta}"

    def test_create_access_token_empty_data(self):
        """Тест: создание токена с пустыми данными."""
        token = create_access_token(data={})
        
        payload = decode_access_token(token)
        
        assert payload is not None, "Токен с пустыми данными должен декодироваться"
        assert "exp" in payload, "Токен должен содержать exp даже с пустыми данными"

    def test_create_access_token_preserves_original_data(self):
        """Тест: функция не модифицирует исходные данные."""
        original_data = {"sub": "test_user", "user_id": 1}
        original_copy = original_data.copy()
        
        create_access_token(data=original_data)
        
        assert original_data == original_copy, \
            "Функция не должна модифицировать исходный словарь data"


# =============================================================================
# ТЕСТЫ ДЕКОДИРОВАНИЯ JWT ТОКЕНОВ (decode_access_token)
# =============================================================================

class TestDecodeAccessToken:
    """Тесты для функции декодирования JWT токенов."""

    def test_decode_access_token_valid_token(self):
        """Тест: декодирование валидного токена."""
        user_data = {"sub": "test_user", "user_id": 123}
        token = create_access_token(data=user_data)
        
        payload = decode_access_token(token)
        
        assert payload is not None, "Валидный токен должен декодироваться"
        assert payload["sub"] == "test_user", "Данные sub должны совпадать"
        assert payload["user_id"] == 123, "Данные user_id должны совпадать"

    def test_decode_access_token_invalid_signature(self):
        """Тест: декодирование токена с невалидной подписью."""
        # Создаём токен с одним ключом
        token = create_access_token(data={"sub": "test_user"})
        
        # Пытаемся декодировать с другим ключом (симулируем через модификацию токена)
        # Для этого создадим токен вручную с неправильной подписью
        import base64
        from jose import jwt as jose_jwt
        
        # Создаём токен с неправильным ключом
        wrong_token = jose_jwt.encode(
            {"sub": "test_user"},
            "wrong_secret_key",
            algorithm=JWT_ALGORITHM
        )
        
        payload = decode_access_token(wrong_token)
        
        assert payload is None, "Токен с неправильной подписью должен возвращать None"

    def test_decode_access_token_malformed_token(self):
        """Тест: декодирование некорректного токена."""
        # Невалидные форматы токенов
        assert decode_access_token("") is None, "Пустая строка должна возвращать None"
        assert decode_access_token("not_a_jwt") is None, "Не JWT формат должен возвращать None"
        assert decode_access_token("abc.def") is None, "Токен с 2 частями должен возвращать None"
        assert decode_access_token("abc.def.ghi.jkl") is None, "Токен с 4 частями должен возвращать None"

    def test_decode_access_token_expired_token(self):
        """Тест: декодирование истёкшего токена."""
        # Создаём токен с очень коротким временем жизни (1 секунда)
        token = create_access_token(
            data={"sub": "test_user"},
            expires_delta=timedelta(seconds=1)
        )
        
        # Ждём 2 секунды для истечения токена
        time.sleep(2)
        
        payload = decode_access_token(token)
        
        assert payload is None, "Истёкший токен должен возвращать None"

    def test_decode_access_token_token_without_sub(self):
        """Тест: декодирование токена без поля sub."""
        # Создаём токен без sub (технически это возможно)
        token = create_access_token(data={"user_id": 123, "role": "admin"})
        
        payload = decode_access_token(token)
        
        assert payload is not None, "Токен без sub должен декодироваться"
        assert "sub" not in payload or payload.get("sub") is None, \
            "Токен без sub не должен содержать sub в payload"


# =============================================================================
# ТЕСТЫ ИЗВЛЕЧЕНИЯ ДАННЫХ ПОЛЬЗОВАТЕЛЯ (get_user_from_token)
# =============================================================================

class TestGetUserFromToken:
    """Тесты для функции get_user_from_token."""

    def test_get_user_from_token_valid_token(self):
        """Тест: извлечение данных из валидного токена."""
        user_data = {"sub": "john_doe", "user_id": 42, "email": "john@example.com"}
        token = create_access_token(data=user_data)
        
        user_info = get_user_from_token(token)
        
        assert user_info is not None, "Данные должны быть извлечены"
        assert user_info["sub"] == "john_doe", "sub должен совпадать"
        assert user_info["user_id"] == 42, "user_id должен совпадать"
        assert user_info["email"] == "john@example.com", "email должен совпадать"

    def test_get_user_from_token_invalid_token(self):
        """Тест: извлечение данных из невалидного токена."""
        user_info = get_user_from_token("invalid_token")
        
        assert user_info is None, "Невалидный токен должен возвращать None"

    def test_get_user_from_token_expired_token(self):
        """Тест: извлечение данных из истёкшего токена."""
        token = create_access_token(
            data={"sub": "test_user"},
            expires_delta=timedelta(seconds=1)
        )
        
        time.sleep(2)
        
        user_info = get_user_from_token(token)
        
        assert user_info is None, "Истёкший токен должен возвращать None"

    def test_get_user_from_token_without_sub(self):
        """Тест: токен без поля sub должен возвращать None."""
        # Создаём токен без sub
        token = create_access_token(data={"user_id": 123})
        
        # get_user_from_token должен вернуть None так как нет sub
        user_info = get_user_from_token(token)
        
        assert user_info is None, "Токен без sub должен возвращать None"


# =============================================================================
# ИНТЕГРАЦИОННЫЕ ТЕСТЫ
# =============================================================================

class TestSecurityIntegration:
    """Интеграционные тесты для модуля безопасности."""

    def test_full_auth_flow(self):
        """Тест: полный поток аутентификации."""
        # 1. Хешируем пароль
        password = "secure_password123"
        hashed = hash_password(password)
        
        # 2. Проверяем пароль
        assert verify_password(password, hashed) is True
        assert verify_password("wrong_password", hashed) is False
        
        # 3. Создаём токен
        user_data = {"sub": "test_user", "user_id": 1, "password_hash": hashed}
        token = create_access_token(data=user_data)
        
        # 4. Декодируем токен
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == "test_user"
        assert payload["user_id"] == 1
        
        # 5. Извлекаем данные пользователя
        user_info = get_user_from_token(token)
        assert user_info is not None
        assert user_info["sub"] == "test_user"

    def test_multiple_users_different_tokens(self):
        """Тест: разные пользователи получают разные токены."""
        users = [
            {"sub": "user1", "user_id": 1},
            {"sub": "user2", "user_id": 2},
            {"sub": "user3", "user_id": 3},
        ]
        
        tokens = [create_access_token(data=user) for user in users]
        
        # Все токены должны быть разными
        assert len(set(tokens)) == len(tokens), "Все токены должны быть уникальными"
        
        # Декодируем и проверяем данные
        for token, user in zip(tokens, users):
            payload = decode_access_token(token)
            assert payload["sub"] == user["sub"]
            assert payload["user_id"] == user["user_id"]

    def test_password_security(self):
        """Тест: безопасность хеширования паролей."""
        passwords = [
            "simple",
            "WithCaps123",
            "medium_length_password_with_some_extra_chars",
            "спецсимволы!@#$%^&*()",
            "emoji🔐🔑🛡️"
        ]

        for password in passwords:
            hashed = hash_password(password)

            # Проверка формата bcrypt
            assert hashed.startswith("$2"), "Хеш должен быть в формате bcrypt"

            # Проверка проверки
            assert verify_password(password, hashed) is True
            assert verify_password("wrong", hashed) is False

    def test_token_expiration_flow(self):
        """Тест: поток истечения токена."""
        # Создаём токен с коротким временем жизни
        token = create_access_token(
            data={"sub": "test_user"},
            expires_delta=timedelta(seconds=3)
        )
        
        # Сразу должен работать
        assert decode_access_token(token) is not None
        
        # Ждём истечения
        time.sleep(4)
        
        # Должен истечь
        assert decode_access_token(token) is None
