"""
Сервис аутентификации для системы Go Problems Trainer.

Этот модуль содержит бизнес-логику для:
- Регистрации новых пользователей
- Аутентификации пользователей (проверка логина/пароля)
- Получения информации о пользователях
- Управления токенами доступа

Функции используют:
- Модель User из backend.models.user
- Функции безопасности из backend.utils.security
- Сессию базы данных SQLAlchemy
"""

from typing import Optional, Tuple
from sqlalchemy.orm import Session

from backend.models.user import User
from backend.utils.security import (
    hash_password,
    verify_password,
    create_access_token,
)
from backend.schemas.user import UserCreate


# =============================================================================
# ИСКЛЮЧЕНИЯ
# =============================================================================

class AuthenticationError(Exception):
    """
    Базовое исключение для ошибок аутентификации.
    
    Выбрасывается при неудачной попытке входа или регистрации.
    """
    pass


class UserAlreadyExistsError(AuthenticationError):
    """
    Исключение для случая, когда пользователь с таким именем уже существует.
    
    Выбрасывается при попытке зарегистрировать пользователя с именем,
    которое уже занято в базе данных.
    """
    pass


class InvalidCredentialsError(AuthenticationError):
    """
    Исключение для случая, когда учётные данные неверны.
    
    Выбрасывается при попытке входа с неправильным паролем
    или когда пользователь не найден.
    """
    pass


# =============================================================================
# ФУНКЦИИ РЕГИСТРАЦИИ И АУТЕНТИФИКАЦИИ
# =============================================================================

def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """
    Получает пользователя из базы данных по имени пользователя.
    
    Функция выполняет поиск пользователя с указанным именем в базе данных.
    Если пользователь найден - возвращает объект User, иначе None.
    
    Args:
        db (Session): Сессия SQLAlchemy для работы с базой данных
        username (str): Имя пользователя для поиска
    
    Returns:
        Optional[User]: Объект User если найден, None в противном случае
    
    Example:
        >>> user = get_user_by_username(db, "john_doe")
        >>> if user:
        ...     print(f"Найден пользователь: {user.user_name}")
        ... else:
        ...     print("Пользователь не найден")
    """
    return db.query(User).filter(User.user_name == username).first()


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """
    Получает пользователя из базы данных по идентификатору.
    
    Функция выполняет поиск пользователя с указанным ID в базе данных.
    Если пользователь найден - возвращает объект User, иначе None.
    
    Args:
        db (Session): Сессия SQLAlchemy для работы с базой данных
        user_id (int): Идентификатор пользователя для поиска
    
    Returns:
        Optional[User]: Объект User если найден, None в противном случае
    
    Example:
        >>> user = get_user_by_id(db, 42)
        >>> if user:
        ...     print(f"Найден пользователь: {user.user_name}")
    """
    return db.query(User).filter(User.user_id == user_id).first()


def register_user(db: Session, user_data: UserCreate) -> User:
    """
    Регистрирует нового пользователя в системе.
    
    Функция выполняет следующие шаги:
    1. Проверяет, не существует ли пользователь с таким именем
    2. Создаёт хэш пароля с помощью bcrypt
    3. Создаёт нового пользователя в базе данных
    4. Возвращает созданного пользователя
    
    Args:
        db (Session): Сессия SQLAlchemy для работы с базой данных
        user_data (UserCreate): Данные пользователя из схемы регистрации
    
    Returns:
        User: Созданный объект пользователя
    
    Raises:
        UserAlreadyExistsError: Если пользователь с таким именем уже существует
    
    Example:
        >>> from backend.schemas.user import UserCreate
        >>> user_data = UserCreate(username="new_user", password="secure123")
        >>> user = register_user(db, user_data)
        >>> print(f"Создан пользователь: {user.user_name}, ID: {user.user_id}")
    
    Security Note:
        - Пароль хешируется с помощью bcrypt перед сохранением
        - Имя пользователя проверяется на уникальность
        - Пароль в открытом виде никогда не сохраняется в БД
    """
    # Проверяем, не существует ли пользователь с таким именем
    existing_user = get_user_by_username(db, user_data.username)
    
    if existing_user:
        # Пользователь уже существует - выбрасываем исключение
        raise UserAlreadyExistsError(
            f"Пользователь с именем '{user_data.username}' уже существует"
        )
    
    # Создаём хэш пароля с помощью bcrypt
    # hash_password автоматически генерирует соль и выполняет многократное хеширование
    password_hash = hash_password(user_data.password)
    
    # Создаём нового пользователя
    db_user = User(
        user_name=user_data.username,
        password_hash=password_hash
    )
    
    # Добавляем пользователя в базу данных
    db.add(db_user)
    
    # Фиксируем изменения (commit)
    # После commit пользователь получает autoincrement user_id
    db.commit()
    
    # Обновляем объект пользователя из БД (чтобы получить user_id)
    db.refresh(db_user)
    
    return db_user


def authenticate_user(
    db: Session, 
    username: str, 
    password: str
) -> Tuple[Optional[User], Optional[str]]:
    """
    Аутентифицирует пользователя по имени и паролю.
    
    Функция выполняет следующие шаги:
    1. Ищет пользователя в базе данных по имени
    2. Если пользователь найден - проверяет пароль с помощью bcrypt
    3. Если пароль верный - создаёт JWT access токен
    4. Возвращает кортеж (пользователь, токен) или (None, ошибка)
    
    Args:
        db (Session): Сессия SQLAlchemy для работы с базой данных
        username (str): Имя пользователя (логин)
        password (str): Пароль пользователя в открытом виде
    
    Returns:
        Tuple[Optional[User], Optional[str]]: 
            - (User, token) если аутентификация успешна
            - (None, error_message) если аутентификация не удалась
    
    Example:
        >>> user, token = authenticate_user(db, "john_doe", "password123")
        >>> if user:
        ...     print(f"Вход выполнен: {user.user_name}")
        ...     print(f"Токен: {token}")
        ... else:
        ...     print(f"Ошибка: {token}")  # token содержит сообщение об ошибке
    
    Security Note:
        - Используется постоянное по времени сравнение паролей (защита от timing attacks)
        - JWT токен создаётся с ограниченным временем жизни (30 минут по умолчанию)
        - Пароль никогда не возвращается и не логируется
    """
    # Ищем пользователя в базе данных
    user = get_user_by_username(db, username)
    
    # Если пользователь не найден - возвращаем ошибку
    # Не указываем конкретно, что пользователь не найден (защита от enumeration)
    if user is None:
        return None, "Неверное имя пользователя или пароль"
    
    # Проверяем пароль с помощью bcrypt
    # verify_password использует постоянное по времени сравнение
    password_valid = verify_password(password, user.password_hash)
    
    # Если пароль неверный - возвращаем ошибку
    if not password_valid:
        return None, "Неверное имя пользователя или пароль"
    
    # Создаём JWT access токен для пользователя
    # Токен содержит user_id и username для последующей идентификации
    token_data = {
        "sub": user.user_name,  # subject - стандартное поле JWT
        "user_id": user.user_id
    }
    
    access_token = create_access_token(data=token_data)
    
    # Возвращаем пользователя и токен
    return user, access_token


def create_user_tokens(db: Session, user: User) -> str:
    """
    Создаёт JWT токены для существующего пользователя.
    
    Функция используется для обновления токенов или создания новых токенов
    для уже аутентифицированного пользователя.
    
    Args:
        db (Session): Сессия SQLAlchemy для работы с базой данных
        user (User): Объект пользователя для которого создаются токены
    
    Returns:
        str: JWT access токен
    
    Example:
        >>> user = get_user_by_id(db, 42)
        >>> token = create_user_tokens(db, user)
        >>> print(f"Новый токен: {token}")
    
    Note:
        В будущем можно добавить создание refresh токенов для обновления
        access токенов без повторной аутентификации.
    """
    # Создаём данные для токена
    token_data = {
        "sub": user.user_name,
        "user_id": user.user_id
    }
    
    # Создаём и возвращаем access токен
    return create_access_token(data=token_data)


# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================================================

def change_user_password(
    db: Session, 
    user: User, 
    old_password: str, 
    new_password: str
) -> bool:
    """
    Изменяет пароль пользователя после проверки старого пароля.
    
    Функция выполняет следующие шаги:
    1. Проверяет старый пароль
    2. Если пароль верный - создаёт хэш нового пароля
    3. Обновляет пароль в базе данных
    
    Args:
        db (Session): Сессия SQLAlchemy для работы с базой данных
        user (User): Объект пользователя
        old_password (str): Текущий пароль пользователя
        new_password (str): Новый пароль
    
    Returns:
        bool: True если пароль успешно изменён, False если старый пароль неверен
    
    Example:
        >>> user = get_user_by_id(db, 42)
        >>> success = change_user_password(db, user, "old_pass", "new_pass123")
        >>> if success:
        ...     print("Пароль успешно изменён")
    
    Security Note:
        - Старый пароль должен быть подтверждён перед изменением
        - Новый пароль хешируется перед сохранением
        - Функция не выбрасывает исключения, а возвращает False при ошибке
    """
    # Проверяем старый пароль
    if not verify_password(old_password, user.password_hash):
        return False
    
    # Создаём хэш нового пароля
    new_password_hash = hash_password(new_password)
    
    # Обновляем пароль в базе данных
    user.password_hash = new_password_hash
    db.commit()
    
    return True
