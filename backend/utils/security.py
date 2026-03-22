"""
Модуль безопасности для приложения Go Problems Trainer.

Этот модуль предоставляет функции для:
- Хеширования паролей с использованием bcrypt
- Проверки паролей
- Создания и декодирования JWT токенов для аутентификации пользователей

Все функции используют лучшие практики безопасности:
- bcrypt для надёжного хеширования с солью
- JWT токены с ограниченным временем жизни
- Алгоритм HS256 для подписи токенов

Примечание:
    Используем bcrypt напрямую вместо passlib для совместимости
    с последними версиями Python и bcrypt.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import JWTError, jwt

# =============================================================================
# КОНФИГУРАЦИЯ БЕЗОПАСНОСТИ
# =============================================================================

# Секретный ключ для подписи JWT токенов
# В production должен храниться в переменных окружения
# Для development используется значение по умолчанию
JWT_SECRET_KEY = "your-secret-key-change-in-production-2026"

# Алгоритм подписи JWT токенов
# HS256 - симметричный алгоритм на основе HMAC с SHA-256
JWT_ALGORITHM = "HS256"

# Время жизни access токена в минутах (30 минут по умолчанию)
# После истечения этого времени пользователю потребуется получить новый токен
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Максимальная длина пароля для bcrypt (ограничение алгоритма)
# bcrypt обрабатывает только первые 72 байта пароля
MAX_PASSWORD_LENGTH = 72


# =============================================================================
# ФУНКЦИИ ХЕШИРОВАНИЯ И ПРОВЕРКИ ПАРОЛЕЙ
# =============================================================================

def hash_password(password: str) -> str:
    """
    Хеширует пароль пользователя с использованием bcrypt.

    bcrypt автоматически:
    - Генерирует случайную соль (salt) для каждого пароля
    - Выполняет множественные раунды хеширования для защиты от brute-force
    - Возвращает строку, содержащую соль и хеш в формате: $algorithm$cost$salt+hash

    Ограничение bcrypt:
        bcrypt поддерживает пароли максимум до 72 байт. Если пароль длиннее,
        он обрезается до 72 байт перед хешированием. Это ограничение самого
        алгоритма bcrypt, а не нашей реализации.

    Args:
        password (str): Исходный пароль пользователя в виде строки

    Returns:
        str: Захешированный пароль (строка длиной ~60 символов)

    Example:
        >>> hashed = hash_password("my_secure_password123")
        >>> print(hashed)
        $2b$12$KIXx... (60 символов)
    """
    # Кодируем пароль в байты
    password_bytes = password.encode('utf-8')
    
    # Обрезаем пароль до 72 байт если он длиннее (ограничение bcrypt)
    if len(password_bytes) > MAX_PASSWORD_LENGTH:
        password_bytes = password_bytes[:MAX_PASSWORD_LENGTH]
    
    # Генерируем соль и хешируем пароль
    # bcrypt.gensalt() создаёт случайную соль
    # round=12 - количество раундов хеширования (по умолчанию)
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    
    # Возвращаем хеш как строку
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверяет соответствие пароля захешированному значению.

    Функция извлекает соль из хеша и выполняет хеширование переданного пароля
    с той же солью. Затем сравнивает результат с исходным хешем.

    Args:
        plain_password (str): Пароль в открытом виде для проверки
        hashed_password (str): Захешированный пароль из базы данных

    Returns:
        bool: True если пароль верный, False в противном случае

    Example:
        >>> hashed = hash_password("my_password")
        >>> verify_password("my_password", hashed)
        True
        >>> verify_password("wrong_password", hashed)
        False

    Security Note:
        Функция использует постоянное по времени сравнение для защиты
        от timing attacks (атак по времени выполнения)
    """
    try:
        # Кодируем пароль в байты
        password_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        
        # Обрезаем пароль до 72 байт если он длиннее (согласуется с hash_password)
        if len(password_bytes) > MAX_PASSWORD_LENGTH:
            password_bytes = password_bytes[:MAX_PASSWORD_LENGTH]
        
        # bcrypt.checkpw безопасно сравнивает хеши
        # Использует постоянное по времени сравнение
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except (ValueError, TypeError):
        # Возвращаем False для невалидных хешей
        # ValueError может быть выброшен для некорректного формата хеша
        return False


# =============================================================================
# ФУНКЦИИ РАБОТЫ С JWT ТОКЕНАМИ
# =============================================================================

def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Создаёт JWT access токен для аутентификации пользователя.

    Токен содержит:
    - claims (утверждения): данные из параметра data (обычно user_id, username)
    - exp (expiration time): время истечения токена
    - iat (issued at): время создания токена
    - sub (subject): идентификатор субъекта токена (пользователя)

    Args:
        data (dict): Данные для кодирования в токене.
                     Обычно содержит {"sub": username, "user_id": 1}
        expires_delta (Optional[timedelta]): Опциональное время жизни токена.
                     Если не указано, используется ACCESS_TOKEN_EXPIRE_MINUTES

    Returns:
        str: JWT токен в формате header.payload.signature (base64url encoded)

    Example:
        >>> token_data = {"sub": "john_doe", "user_id": 42}
        >>> token = create_access_token(token_data)
        >>> print(token)
        eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJqb2huX2RvZSJ9...

    JWT Structure:
        - Header: {"alg": "HS256", "typ": "JWT"}
        - Payload: {"sub": "john_doe", "user_id": 42, "exp": 1234567890, "iat": 1234567800}
        - Signature: HMACSHA256(header + "." + payload, secret_key)
    """
    # Копируем данные для модификации
    to_encode = data.copy()

    # Вычисляем время истечения токена
    if expires_delta:
        # Если передано кастомное время жизни - используем его
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        # Иначе используем время по умолчанию из конфигурации
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )

    # Добавляем стандартные claims (утверждения JWT)
    # "exp" - время истечения токена (обязательно для безопасности)
    to_encode.update({"exp": expire})
    
    # "iat" - время создания токена (issued at)
    # Добавляем вручную для явного контроля
    to_encode.update({"iat": datetime.now(timezone.utc)})
    
    # "sub" - идентификатор субъекта (должен быть передан в data)
    # "jti" - уникальный идентификатор токена (опционально)

    # Кодируем токен с использованием секретного ключа и алгоритма
    encoded_jwt = jwt.encode(
        to_encode,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM
    )

    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """
    Декодирует и проверяет JWT access токен.

    Функция выполняет:
    - Проверку подписи токена с использованием JWT_SECRET_KEY
    - Проверку времени истечения токена (exp claim)
    - Извлечение данных из токена

    Args:
        token (str): JWT токен в формате header.payload.signature

    Returns:
        Optional[dict]: Словарь с данными из токена если токен валиден,
                        None если токен невалиден или истёк

    Example:
        >>> token = create_access_token({"sub": "john_doe", "user_id": 42})
        >>> payload = decode_access_token(token)
        >>> print(payload)
        {"sub": "john_doe", "user_id": 42, "exp": 1234567890, "iat": 1234567800}

        >>> expired_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.expired..."
        >>> decode_access_token(expired_token)
        None

    Security Note:
        Функция автоматически отклоняет токены:
        - С истёкшим сроком действия (exp < now)
        - С невалидной подписью
        - С некорректным форматом
    """
    try:
        # jwt.decode() автоматически:
        # - Проверяет подпись токена
        # - Проверяет время истечения (exp claim)
        # - Проверяет формат токена
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        # JWTError выбрасывается при:
        # - Истёкшем сроке действия (ExpiredSignatureError)
        # - Невалидной подписи (InvalidSignatureError)
        # - Невалидном формате (DecodeError)
        # Возвращаем None для безопасной обработки ошибок
        return None


# =============================================================================
# ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ ДАННЫХ ПОЛЬЗОВАТЕЛЯ ИЗ ТОКЕНА
# =============================================================================

def get_user_from_token(token: str) -> Optional[dict]:
    """
    Извлекает информацию о пользователе из JWT токена.

    Это обёртка над decode_access_token(), которая дополнительно
    проверяет наличие обязательных полей пользователя в токене.

    Args:
        token (str): JWT токен для декодирования

    Returns:
        Optional[dict]: Словарь с информацией о пользователе если токен валиден
                        и содержит required поля, None в противном случае

    Example:
        >>> token = create_access_token({"sub": "john_doe", "user_id": 42})
        >>> user_info = get_user_from_token(token)
        >>> print(user_info)
        {"sub": "john_doe", "user_id": 42, "exp": ..., "iat": ...}
    """
    payload = decode_access_token(token)
    
    if payload is None:
        return None
    
    # Проверяем наличие обязательного поля "sub" (subject - username)
    # Это стандартное поле JWT, которое должно присутствовать всегда
    if "sub" not in payload:
        return None
    
    return payload
