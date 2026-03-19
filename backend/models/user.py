"""
Модель пользователя для системы аутентификации.

Содержит базовые поля для регистрации и авторизации пользователей:
- user_id: уникальный идентификатор пользователя (первичный ключ)
- user_name: уникальное имя пользователя (логин)
- password_hash: хэш пароля (bcrypt)

Модель используется для хранения учётных данных и управления доступом.
"""

from typing import TYPE_CHECKING, List
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from backend.database import Base

# Отложенный импорт для избежания циклической зависимости
if TYPE_CHECKING:
    from backend.models.solved_task import SolvedTask


class User(Base):
    """
    Модель пользователя в базе данных.

    Атрибуты:
        __tablename__ (str): Имя таблицы в БД - 'users'
        user_id (int): Уникальный идентификатор пользователя, первичный ключ
        user_name (str): Уникальное имя пользователя (логин), индексировано
        password_hash (str): Хэш пароля, созданный с помощью bcrypt

    Связи:
        solved_tasks: Список решённых задач пользователя (один ко многим)
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

    # Связь с решёнными задачами (один ко многим)
    # Каскадное удаление: при удалении пользователя удаляются все его решённые задачи
    # back_populates: двусторонняя связь с моделью SolvedTask
    solved_tasks = relationship(
        "SolvedTask",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    def __repr__(self) -> str:
        """
        Строковое представление пользователя для отладки.

        Returns:
            str: Строка вида '<User username>'
        """
        return f"<User {self.user_name}>"
