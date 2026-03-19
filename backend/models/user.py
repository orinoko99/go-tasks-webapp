"""
Модель пользователя для системы аутентификации.

Содержит базовые поля для регистрации и авторизации пользователей:
- user_id: уникальный идентификатор пользователя (первичный ключ)
- user_name: уникальное имя пользователя (логин)
- password_hash: хэш пароля (bcrypt)

Модель используется для хранения учётных данных и управления доступом.

Примечание:
    Связь с SolvedTask будет добавлена после создания модели SolvedTask.
"""

from sqlalchemy import Column, Integer, String

from backend.database import Base


class User(Base):
    """
    Модель пользователя в базе данных.
    
    Атрибуты:
        __tablename__ (str): Имя таблицы в БД - 'users'
        user_id (int): Уникальный идентификатор пользователя, первичный ключ
        user_name (str): Уникальное имя пользователя (логин), индексировано
        password_hash (str): Хэш пароля, созданный с помощью bcrypt
    """
    
    __tablename__ = "users"
    
    # Первичный ключ: автоинкрементируемый идентификатор
    user_id = Column(Integer, primary_key=True, index=True)
    
    # Имя пользователя: уникальное, обязательное поле
    # Индексируется для ускорения поиска при аутентификации
    user_name = Column(String(50), unique=True, index=True, nullable=False)
    
    # Хэш пароля: обязательное поле
    # Хранит bcrypt хэш для безопасной аутентификации
    password_hash = Column(String(255), nullable=False)
    
    def __repr__(self) -> str:
        """
        Строковое представление пользователя для отладки.
        
        Returns:
            str: Строка вида '<User username>'
        """
        return f"<User {self.user_name}>"
