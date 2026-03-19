# Модели данных

from backend.models.user import User

# Импортируем SolvedTask после создания User для избежания циклических зависимостей
# from backend.models.solved_task import SolvedTask

__all__ = ["User"]
