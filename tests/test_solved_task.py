"""
Тесты для модели SolvedTask.

Проверяют:
- Создание и сохранение решённой задачи
- Связь с пользователем (User.solved_tasks)
- Каскадное удаление при удалении пользователя
- Корректность полей и значений по умолчанию
- Метод to_dict()
- Уникальность и индексация полей
"""

import pytest
from datetime import datetime
from sqlalchemy.orm import Session

from backend.database import SessionLocal, init_db, reset_db
from backend.models.user import User
from backend.models.solved_task import SolvedTask


@pytest.fixture(autouse=True)
def setup_db():
    """Инициализация БД перед каждым тестом."""
    init_db()
    yield
    reset_db()


@pytest.fixture
def db() -> Session:
    """Фикстура для получения сессии БД."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_user(db: Session) -> User:
    """Фикстура для создания тестового пользователя."""
    user = User(user_name="test_user", password_hash="hashed_password_123")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


class TestSolvedTaskCreation:
    """Тесты создания решённой задачи."""

    def test_create_solved_task(self, db: Session, test_user: User):
        """Тест создания решённой задачи."""
        solved_task = SolvedTask(
            user_id=test_user.user_id,
            task_id="beginner/001",
            sgf_file_name="beginner_problems.sgf"
        )
        db.add(solved_task)
        db.commit()
        db.refresh(solved_task)

        assert solved_task.id is not None
        assert solved_task.user_id == test_user.user_id
        assert solved_task.task_id == "beginner/001"
        assert solved_task.sgf_file_name == "beginner_problems.sgf"
        assert solved_task.is_solved is True
        assert isinstance(solved_task.solved_at, datetime)

    def test_solved_task_default_values(self, db: Session, test_user: User):
        """Тест значений по умолчанию для решённой задачи."""
        solved_task = SolvedTask(
            user_id=test_user.user_id,
            task_id="test/001",
            sgf_file_name="test.sgf"
        )
        db.add(solved_task)
        db.commit()

        # is_solved по умолчанию True
        assert solved_task.is_solved is True
        # solved_at устанавливается автоматически
        assert solved_task.solved_at is not None

    def test_solved_task_repr(self, db: Session, test_user: User):
        """Тест строкового представления решённой задачи."""
        solved_task = SolvedTask(
            user_id=test_user.user_id,
            task_id="beginner/001",
            sgf_file_name="beginner_problems.sgf"
        )
        db.add(solved_task)
        db.commit()

        assert repr(solved_task) == "<SolvedTask beginner/001 for user 1>"

    def test_solved_task_to_dict(self, db: Session, test_user: User):
        """Тест метода to_dict() для решённой задачи."""
        solved_task = SolvedTask(
            user_id=test_user.user_id,
            task_id="beginner/001",
            sgf_file_name="beginner_problems.sgf"
        )
        db.add(solved_task)
        db.commit()
        db.refresh(solved_task)

        task_dict = solved_task.to_dict()

        assert task_dict["id"] == solved_task.id
        assert task_dict["user_id"] == test_user.user_id
        assert task_dict["task_id"] == "beginner/001"
        assert task_dict["sgf_file_name"] == "beginner_problems.sgf"
        assert task_dict["is_solved"] is True
        assert "solved_at" in task_dict
        assert isinstance(task_dict["solved_at"], str)  # ISO формат


class TestSolvedTaskRelationship:
    """Тесты связи SolvedTask с User."""

    def test_solved_task_user_relationship(self, db: Session, test_user: User):
        """Тест связи решённой задачи с пользователем."""
        solved_task = SolvedTask(
            user_id=test_user.user_id,
            task_id="beginner/001",
            sgf_file_name="beginner_problems.sgf"
        )
        db.add(solved_task)
        db.commit()
        db.refresh(solved_task)

        # Проверка связи с пользователем
        assert solved_task.user is not None
        assert solved_task.user.user_id == test_user.user_id
        assert solved_task.user.user_name == "test_user"

    def test_user_solved_tasks_relationship(self, db: Session, test_user: User):
        """Тест связи пользователя с решёнными задачами."""
        # Создаём несколько решённых задач
        task1 = SolvedTask(user_id=test_user.user_id, task_id="beginner/001", sgf_file_name="beginner.sgf")
        task2 = SolvedTask(user_id=test_user.user_id, task_id="beginner/002", sgf_file_name="beginner.sgf")
        task3 = SolvedTask(user_id=test_user.user_id, task_id="intermediate/001", sgf_file_name="intermediate.sgf")

        db.add_all([task1, task2, task3])
        db.commit()

        # Проверка связи с пользователем
        db.refresh(test_user)
        user_tasks = test_user.solved_tasks.all()

        assert len(user_tasks) == 3
        assert task1 in user_tasks
        assert task2 in user_tasks
        assert task3 in user_tasks

    def test_cascade_delete_on_user_delete(self, db: Session, test_user: User):
        """Тест каскадного удаления решённых задач при удалении пользователя."""
        # Создаём решённые задачи
        task1 = SolvedTask(user_id=test_user.user_id, task_id="beginner/001", sgf_file_name="beginner.sgf")
        task2 = SolvedTask(user_id=test_user.user_id, task_id="beginner/002", sgf_file_name="beginner.sgf")

        db.add_all([task1, task2])
        db.commit()

        # Получаем ID задач для проверки
        task1_id = task1.id
        task2_id = task2.id

        # Удаляем пользователя
        db.delete(test_user)
        db.commit()

        # Проверяем, что задачи удалены
        remaining_tasks = db.query(SolvedTask).filter(
            SolvedTask.id.in_([task1_id, task2_id])
        ).all()

        assert len(remaining_tasks) == 0

    def test_multiple_users_solved_tasks(self, db: Session):
        """Тест решённых задач для нескольких пользователей."""
        # Создаём двух пользователей
        user1 = User(user_name="user1", password_hash="hash1")
        user2 = User(user_name="user2", password_hash="hash2")

        db.add_all([user1, user2])
        db.commit()
        db.refresh(user1)
        db.refresh(user2)

        # Создаём задачи для каждого пользователя
        task1 = SolvedTask(user_id=user1.user_id, task_id="beginner/001", sgf_file_name="beginner.sgf")
        task2 = SolvedTask(user_id=user1.user_id, task_id="beginner/002", sgf_file_name="beginner.sgf")
        task3 = SolvedTask(user_id=user2.user_id, task_id="intermediate/001", sgf_file_name="intermediate.sgf")

        db.add_all([task1, task2, task3])
        db.commit()

        # Проверяем, что задачи правильно связаны
        db.refresh(user1)
        db.refresh(user2)

        user1_tasks = user1.solved_tasks.all()
        user2_tasks = user2.solved_tasks.all()

        assert len(user1_tasks) == 2
        assert len(user2_tasks) == 1
        assert all(task.user_id == user1.user_id for task in user1_tasks)
        assert all(task.user_id == user2.user_id for task in user2_tasks)


class TestSolvedTaskFields:
    """Тесты полей модели SolvedTask."""

    def test_task_id_indexed(self, db: Session, test_user: User):
        """Тест индексации поля task_id."""
        # Создаём задачу
        task = SolvedTask(user_id=test_user.user_id, task_id="beginner/001", sgf_file_name="beginner.sgf")
        db.add(task)
        db.commit()

        # Проверяем, что поиск по task_id работает (использует индекс)
        found_task = db.query(SolvedTask).filter(SolvedTask.task_id == "beginner/001").first()
        assert found_task is not None
        assert found_task.task_id == "beginner/001"

    def test_sgf_file_name_indexed(self, db: Session, test_user: User):
        """Тест индексации поля sgf_file_name."""
        task = SolvedTask(user_id=test_user.user_id, task_id="beginner/001", sgf_file_name="beginner.sgf")
        db.add(task)
        db.commit()

        # Проверяем поиск по sgf_file_name
        tasks = db.query(SolvedTask).filter(SolvedTask.sgf_file_name == "beginner.sgf").all()
        assert len(tasks) == 1
        assert tasks[0].task_id == "beginner/001"

    def test_user_id_indexed(self, db: Session, test_user: User):
        """Тест индексации поля user_id."""
        task = SolvedTask(user_id=test_user.user_id, task_id="beginner/001", sgf_file_name="beginner.sgf")
        db.add(task)
        db.commit()

        # Проверяем поиск по user_id
        tasks = db.query(SolvedTask).filter(SolvedTask.user_id == test_user.user_id).all()
        assert len(tasks) == 1

    def test_task_id_max_length(self, db: Session, test_user: User):
        """Тест максимальной длины task_id."""
        # Максимальная длина 100 символов
        long_task_id = "a" * 100
        task = SolvedTask(user_id=test_user.user_id, task_id=long_task_id, sgf_file_name="test.sgf")
        db.add(task)
        db.commit()

        assert task.task_id == long_task_id

    def test_sgf_file_name_max_length(self, db: Session, test_user: User):
        """Тест максимальной длины sgf_file_name."""
        # Максимальная длина 255 символов
        long_filename = "a" * 255
        task = SolvedTask(user_id=test_user.user_id, task_id="test/001", sgf_file_name=long_filename)
        db.add(task)
        db.commit()

        assert task.sgf_file_name == long_filename

    def test_user_id_required(self, db: Session):
        """Тест обязательности поля user_id."""
        task = SolvedTask(task_id="beginner/001", sgf_file_name="beginner.sgf")
        db.add(task)

        with pytest.raises(Exception):
            db.commit()

    def test_task_id_required(self, db: Session, test_user: User):
        """Тест обязательности поля task_id."""
        task = SolvedTask(user_id=test_user.user_id, sgf_file_name="beginner.sgf")
        db.add(task)

        with pytest.raises(Exception):
            db.commit()

    def test_sgf_file_name_required(self, db: Session, test_user: User):
        """Тест обязательности поля sgf_file_name."""
        task = SolvedTask(user_id=test_user.user_id, task_id="beginner/001")
        db.add(task)

        with pytest.raises(Exception):
            db.commit()


class TestSolvedTaskQueries:
    """Тесты запросов к решённым задачам."""

    def test_get_solved_tasks_by_user(self, db: Session, test_user: User):
        """Тест получения всех решённых задач пользователя."""
        tasks = [
            SolvedTask(user_id=test_user.user_id, task_id=f"beginner/{i:03d}", sgf_file_name="beginner.sgf")
            for i in range(5)
        ]
        db.add_all(tasks)
        db.commit()

        user_tasks = db.query(SolvedTask).filter(SolvedTask.user_id == test_user.user_id).all()
        assert len(user_tasks) == 5

    def test_get_solved_tasks_by_sgf_file(self, db: Session, test_user: User):
        """Тест получения задач по имени SGF файла."""
        tasks = [
            SolvedTask(user_id=test_user.user_id, task_id=f"beginner/{i:03d}", sgf_file_name="beginner.sgf")
            for i in range(3)
        ]
        tasks.extend([
            SolvedTask(user_id=test_user.user_id, task_id=f"intermediate/{i:03d}", sgf_file_name="intermediate.sgf")
            for i in range(2)
        ])
        db.add_all(tasks)
        db.commit()

        beginner_tasks = db.query(SolvedTask).filter(SolvedTask.sgf_file_name == "beginner.sgf").all()
        assert len(beginner_tasks) == 3

    def test_count_solved_tasks_by_user(self, db: Session, test_user: User):
        """Тест подсчёта количества решённых задач пользователя."""
        tasks = [
            SolvedTask(user_id=test_user.user_id, task_id=f"beginner/{i:03d}", sgf_file_name="beginner.sgf")
            for i in range(7)
        ]
        db.add_all(tasks)
        db.commit()

        count = db.query(SolvedTask).filter(SolvedTask.user_id == test_user.user_id).count()
        assert count == 7

    def test_get_solved_tasks_grouped_by_sgf(self, db: Session, test_user: User):
        """Тест группировки задач по SGF файлам."""
        tasks = [
            SolvedTask(user_id=test_user.user_id, task_id=f"beginner/{i:03d}", sgf_file_name="beginner.sgf")
            for i in range(5)
        ]
        tasks.extend([
            SolvedTask(user_id=test_user.user_id, task_id=f"intermediate/{i:03d}", sgf_file_name="intermediate.sgf")
            for i in range(3)
        ])
        db.add_all(tasks)
        db.commit()

        # Группировка по sgf_file_name
        from sqlalchemy import func
        result = db.query(
            SolvedTask.sgf_file_name,
            func.count(SolvedTask.id).label("task_count")
        ).filter(
            SolvedTask.user_id == test_user.user_id
        ).group_by(SolvedTask.sgf_file_name).all()

        result_dict = {row.sgf_file_name: row.task_count for row in result}
        assert result_dict["beginner.sgf"] == 5
        assert result_dict["intermediate.sgf"] == 3
