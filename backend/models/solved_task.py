"""
Модель решённой задачи для отслеживания прогресса пользователей.

Хранит информацию о задачах, которые пользователь решил:
- id: уникальный идентификатор записи (первичный ключ)
- user_id: внешний ключ на таблицу пользователей
- task_id: идентификатор задачи (уникальный в рамках SGF файла)
- sgf_file_name: имя файла сборника задач (SGF)
- is_solved: флаг успешного решения задачи
- solved_at: дата и время решения задачи

Модель используется для:
- Отслеживания прогресса пользователя по сборникам
- Отображения решённых задач в интерфейсе (зелёные галочки)
- Подсчёта статистики (количество решённых задач, прогресс по сборникам)
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from backend.database import Base

# Отложенный импорт для избежания циклической зависимости
if TYPE_CHECKING:
    from backend.models.user import User


def utc_now() -> datetime:
    """Возвращает текущее время в UTC."""
    return datetime.now(timezone.utc)


class SolvedTask(Base):
    """
    Модель решённой задачи в базе данных.

    Атрибуты:
        __tablename__ (str): Имя таблицы в БД - 'solved_tasks'
        id (int): Уникальный идентификатор записи, первичный ключ
        user_id (int): Внешний ключ на таблицу пользователей
        task_id (str): Идентификатор задачи (уникальный в рамках SGF файла)
        sgf_file_name (str): Имя файла сборника задач (SGF)
        is_solved (bool): Флаг успешного решения задачи
        solved_at (datetime): Дата и время решения задачи

    Связи:
        user: Связь с моделью User (многие к одному)
    """

    __tablename__ = "solved_tasks"

    # Первичный ключ: автоинкрементируемый идентификатор
    id = Column(Integer, primary_key=True, index=True)

    # Внешний ключ на таблицу пользователей
    # Каскадное удаление: при удалении пользователя удаляются все его решённые задачи
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)

    # Идентификатор задачи (уникальный в рамках SGF файла)
    # Формат: "collection_name/task_index" например "beginner/001"
    task_id = Column(String(100), nullable=False, index=True)

    # Имя файла сборника задач (SGF)
    # Используется для группировки задач по сборникам
    sgf_file_name = Column(String(255), nullable=False, index=True)

    # Флаг успешного решения задачи
    # True - задача решена, False - задача в процессе решения
    is_solved = Column(Boolean, default=True, nullable=False)

    # Дата и время решения задачи
    # Заполняется автоматически при первом решении
    solved_at = Column(DateTime, default=utc_now, nullable=False)

    # Связь с пользователем (многие к одному)
    # back_populates: двусторонняя связь с моделью User
    user = relationship("User", back_populates="solved_tasks")

    def __repr__(self) -> str:
        """
        Строковое представление решённой задачи для отладки.

        Returns:
            str: Строка вида '<SolvedTask task_id for user_id>'
        """
        return f"<SolvedTask {self.task_id} for user {self.user_id}>"

    def to_dict(self) -> dict:
        """
        Преобразование модели в словарь.

        Returns:
            dict: Словарь с данными о решённой задаче
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "task_id": self.task_id,
            "sgf_file_name": self.sgf_file_name,
            "is_solved": self.is_solved,
            "solved_at": self.solved_at.replace(tzinfo=None).isoformat() if self.solved_at else None
        }
