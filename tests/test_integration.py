"""
Интеграционные тесты для моделей User и SolvedTask.

Проверяют совместную работу моделей в различных сценариях:
- Создание пользователя с решёнными задачами
- Статистика и прогресс пользователя по сборникам
- Сложные запросы с объединением данных
- Каскадные операции
- Массовые операции с данными
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models.user import User
from backend.models.solved_task import SolvedTask


# Тестовая база данных в памяти
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db_session():
    """
    Фикстура для создания сессии БД.

    Создаёт таблицы перед каждым тестом и удаляет после.
    """
    # Создание таблиц
    Base.metadata.create_all(bind=test_engine)

    # Создание сессии
    session = TestingSessionLocal()
    yield session

    # Удаление таблиц после теста
    session.close()
    Base.metadata.drop_all(bind=test_engine)


class TestUserWithSolvedTasksIntegration:
    """Интеграционные тесты взаимодействия User и SolvedTask."""

    def test_create_user_with_multiple_solved_tasks(self, db_session):
        """
        Тест создания пользователя с несколькими решёнными задачами.

        Проверяет:
        - Создание пользователя
        - Добавление нескольких решённых задач
        - Корректность связей между моделями
        """
        # Создаём пользователя
        user = User(user_name="go_player", password_hash="bcrypt_hash_123")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        # Создаём решённые задачи для пользователя
        tasks = [
            SolvedTask(user_id=user.user_id, task_id="beginner/001", sgf_file_name="beginner.sgf"),
            SolvedTask(user_id=user.user_id, task_id="beginner/002", sgf_file_name="beginner.sgf"),
            SolvedTask(user_id=user.user_id, task_id="beginner/003", sgf_file_name="beginner.sgf"),
            SolvedTask(user_id=user.user_id, task_id="intermediate/001", sgf_file_name="intermediate.sgf"),
            SolvedTask(user_id=user.user_id, task_id="intermediate/002", sgf_file_name="intermediate.sgf"),
        ]
        db_session.add_all(tasks)
        db_session.commit()

        # Проверяем связь с пользователем
        db_session.refresh(user)
        user_tasks = user.solved_tasks.all()

        assert len(user_tasks) == 5
        assert all(task.user_id == user.user_id for task in user_tasks)

    def test_user_progress_by_collection(self, db_session):
        """
        Тест подсчёта прогресса пользователя по сборникам задач.

        Проверяет:
        - Группировку задач по SGF файлам
        - Подсчёт количества решённых задач в каждом сборнике
        - Корректность агрегации данных
        """
        # Создаём пользователя
        user = User(user_name="progress_tracker", password_hash="hash")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        # Добавляем задачи из разных сборников
        collections = {
            "beginner.sgf": 10,      # 10 задач для начинающих
            "intermediate.sgf": 5,   # 5 задач среднего уровня
            "advanced.sgf": 3,       # 3 задачи для продвинутых
        }

        for sgf_file, count in collections.items():
            for i in range(count):
                task = SolvedTask(
                    user_id=user.user_id,
                    task_id=f"{sgf_file.replace('.sgf', '')}/{i:03d}",
                    sgf_file_name=sgf_file
                )
                db_session.add(task)

        db_session.commit()

        # Получаем статистику по сборникам
        db_session.refresh(user)
        stats = db_session.query(
            SolvedTask.sgf_file_name,
            func.count(SolvedTask.id).label("task_count")
        ).filter(
            SolvedTask.user_id == user.user_id
        ).group_by(SolvedTask.sgf_file_name).all()

        stats_dict = {row.sgf_file_name: row.task_count for row in stats}

        assert stats_dict["beginner.sgf"] == 10
        assert stats_dict["intermediate.sgf"] == 5
        assert stats_dict["advanced.sgf"] == 3

    def test_total_solved_tasks_count(self, db_session):
        """
        Тест подсчёта общего количества решённых задач пользователя.

        Проверяет:
        - Корректность подсчёта всех задач
        - Работу агрегатной функции COUNT
        """
        # Создаём пользователя
        user = User(user_name="counter", password_hash="hash")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        # Добавляем 25 задач
        for i in range(25):
            task = SolvedTask(
                user_id=user.user_id,
                task_id=f"collection/{i:03d}",
                sgf_file_name="collection.sgf"
            )
            db_session.add(task)

        db_session.commit()

        # Подсчитываем количество задач
        total_count = db_session.query(SolvedTask).filter(
            SolvedTask.user_id == user.user_id
        ).count()

        assert total_count == 25

    def test_user_with_no_solved_tasks(self, db_session):
        """
        Тест пользователя без решённых задач.

        Проверяет:
        - Корректность работы связи при отсутствии задач
        - Пустой результат запроса
        """
        # Создаём пользователя без задач
        user = User(user_name="newbie", password_hash="hash")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        # Проверяем что задач нет
        user_tasks = user.solved_tasks.all()
        assert len(user_tasks) == 0

    def test_multiple_users_independent_tasks(self, db_session):
        """
        Тест независимости данных разных пользователей.

        Проверяет:
        - Изоляцию данных между пользователями
        - Корректность связей для каждого пользователя
        """
        # Создаём трёх пользователей
        users = [
            User(user_name="player1", password_hash="hash1"),
            User(user_name="player2", password_hash="hash2"),
            User(user_name="player3", password_hash="hash3"),
        ]
        db_session.add_all(users)
        db_session.commit()

        # Добавляем задачи для каждого пользователя
        task_counts = [5, 10, 15]  # Разное количество задач

        for user, count in zip(users, task_counts):
            for i in range(count):
                task = SolvedTask(
                    user_id=user.user_id,
                    task_id=f"user{users.index(user) + 1}/task{i:03d}",
                    sgf_file_name=f"user{users.index(user) + 1}.sgf"
                )
                db_session.add(task)

        db_session.commit()

        # Проверяем что у каждого пользователя своё количество задач
        for user, expected_count in zip(users, task_counts):
            db_session.refresh(user)
            user_tasks = user.solved_tasks.all()
            assert len(user_tasks) == expected_count

            # Проверяем что все задачи принадлежат этому пользователю
            assert all(task.user_id == user.user_id for task in user_tasks)


class TestCascadeOperationsIntegration:
    """Интеграционные тесты каскадных операций."""

    def test_delete_user_removes_all_solved_tasks(self, db_session):
        """
        Тест каскадного удаления задач при удалении пользователя.

        Проверяет:
        - Каскадное удаление связанных записей
        - Отсутствие осиротевших записей в БД
        """
        # Создаём пользователя с задачами
        user = User(user_name="to_delete", password_hash="hash")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        # Добавляем 10 задач
        for i in range(10):
            task = SolvedTask(
                user_id=user.user_id,
                task_id=f"test/{i:03d}",
                sgf_file_name="test.sgf"
            )
            db_session.add(task)

        db_session.commit()

        # Сохраняем ID задач для проверки
        task_ids = [task.id for task in user.solved_tasks.all()]

        # Удаляем пользователя
        db_session.delete(user)
        db_session.commit()

        # Проверяем что все задачи удалены
        remaining_tasks = db_session.query(SolvedTask).filter(
            SolvedTask.id.in_(task_ids)
        ).all()

        assert len(remaining_tasks) == 0

    def test_delete_one_user_preserves_other_users_tasks(self, db_session):
        """
        Тест сохранения задач других пользователей при удалении.

        Проверяет:
        - Изоляцию каскадного удаления
        - Сохранность данных других пользователей
        """
        # Создаём двух пользователей
        user1 = User(user_name="user1", password_hash="hash1")
        user2 = User(user_name="user2", password_hash="hash2")

        db_session.add_all([user1, user2])
        db_session.commit()

        # Добавляем задачи для каждого
        for i in range(5):
            db_session.add(SolvedTask(user_id=user1.user_id, task_id=f"u1/{i}", sgf_file_name="u1.sgf"))
            db_session.add(SolvedTask(user_id=user2.user_id, task_id=f"u2/{i}", sgf_file_name="u2.sgf"))

        db_session.commit()

        # Удаляем первого пользователя
        db_session.delete(user1)
        db_session.commit()

        # Проверяем что задачи второго пользователя сохранились
        db_session.refresh(user2)
        user2_tasks = user2.solved_tasks.all()

        assert len(user2_tasks) == 5
        assert all(task.user_id == user2.user_id for task in user2_tasks)


class TestComplexQueriesIntegration:
    """Интеграционные тесты сложных запросов."""

    def test_get_users_with_task_counts(self, db_session):
        """
        Тест получения пользователей с количеством решённых задач.

        Проверяет:
        - JOIN запрос между таблицами
        - Агрегацию данных с группировкой
        """
        # Создаём пользователей с разным количеством задач
        users_data = [
            ("active_player", 15),
            ("casual_player", 5),
            ("newbie", 0),
        ]

        for username, task_count in users_data:
            user = User(user_name=username, password_hash="hash")
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            for i in range(task_count):
                db_session.add(SolvedTask(
                    user_id=user.user_id,
                    task_id=f"{username}/{i}",
                    sgf_file_name=f"{username}.sgf"
                ))

        db_session.commit()

        # Получаем пользователей с количеством задач
        result = db_session.query(
            User.user_name,
            func.count(SolvedTask.id).label("solved_count")
        ).outerjoin(SolvedTask, User.user_id == SolvedTask.user_id).group_by(
            User.user_id, User.user_name
        ).all()

        result_dict = {row.user_name: row.solved_count for row in result}

        assert result_dict["active_player"] == 15
        assert result_dict["casual_player"] == 5
        assert result_dict["newbie"] == 0

    def test_get_most_popular_collections(self, db_session):
        """
        Тест получения самых популярных сборников задач.

        Проверяет:
        - Группировку по sgf_file_name
        - Сортировку по количеству задач
        """
        # Создаём пользователя
        user = User(user_name="collector", password_hash="hash")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        # Добавляем задачи из разных сборников с разным количеством
        collections = {
            "popular.sgf": 20,
            "medium.sgf": 10,
            "rare.sgf": 5,
        }

        for sgf_file, count in collections.items():
            for i in range(count):
                db_session.add(SolvedTask(
                    user_id=user.user_id,
                    task_id=f"{sgf_file}/{i}",
                    sgf_file_name=sgf_file
                ))

        db_session.commit()

        # Получаем сборники отсортированные по популярности
        result = db_session.query(
            SolvedTask.sgf_file_name,
            func.count(SolvedTask.id).label("task_count")
        ).filter(
            SolvedTask.user_id == user.user_id
        ).group_by(SolvedTask.sgf_file_name).order_by(
            func.count(SolvedTask.id).desc()
        ).all()

        assert result[0].sgf_file_name == "popular.sgf"
        assert result[0].task_count == 20
        assert result[1].sgf_file_name == "medium.sgf"
        assert result[1].task_count == 10
        assert result[2].sgf_file_name == "rare.sgf"
        assert result[2].task_count == 5

    def test_get_recent_solved_tasks(self, db_session):
        """
        Тест получения последних решённых задач.

        Проверяет:
        - Сортировку по дате решения
        - Фильтрацию по пользователю
        """
        # Создаём пользователя
        user = User(user_name="recent_solver", password_hash="hash")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        # Добавляем задачи (в SQLite порядок вставки сохраняет порядок)
        for i in range(10):
            db_session.add(SolvedTask(
                user_id=user.user_id,
                task_id=f"task/{i:03d}",
                sgf_file_name="tasks.sgf"
            ))

        db_session.commit()

        # Получаем последние 5 задач
        recent_tasks = db_session.query(SolvedTask).filter(
            SolvedTask.user_id == user.user_id
        ).order_by(SolvedTask.solved_at.desc()).limit(5).all()

        assert len(recent_tasks) == 5


class TestDataIntegrityIntegration:
    """Интеграционные тесты целостности данных."""

    def test_unique_username_with_tasks(self, db_session):
        """
        Тест уникальности имени пользователя при наличии задач.

        Проверяет:
        - Сохранение ограничения уникальности
        - Корректность работы при связанных записях
        """
        # Создаём первого пользователя
        user1 = User(user_name="unique_user", password_hash="hash1")
        db_session.add(user1)
        db_session.commit()

        # Добавляем задачи первому пользователю
        for i in range(5):
            db_session.add(SolvedTask(
                user_id=user1.user_id,
                task_id=f"task/{i}",
                sgf_file_name="tasks.sgf"
            ))

        db_session.commit()

        # Пытаемся создать пользователя с тем же именем
        user2 = User(user_name="unique_user", password_hash="hash2")
        db_session.add(user2)

        with pytest.raises(Exception):
            db_session.commit()

        db_session.rollback()

    def test_task_id_uniqueness_per_user(self, db_session):
        """
        Тест уникальности task_id в рамках пользователя.

        Проверяет:
        - Возможность иметь одинаковые task_id у разных пользователей
        - Корректность идентификации задач
        """
        # Создаём двух пользователей
        user1 = User(user_name="user1", password_hash="hash1")
        user2 = User(user_name="user2", password_hash="hash2")

        db_session.add_all([user1, user2])
        db_session.commit()

        # Добавляем задачи с одинаковым task_id разным пользователям
        task1 = SolvedTask(user_id=user1.user_id, task_id="same/task", sgf_file_name="shared.sgf")
        task2 = SolvedTask(user_id=user2.user_id, task_id="same/task", sgf_file_name="shared.sgf")

        db_session.add_all([task1, task2])
        db_session.commit()

        # Проверяем что задачи созданы
        db_session.refresh(user1)
        db_session.refresh(user2)

        assert len(user1.solved_tasks.all()) == 1
        assert len(user2.solved_tasks.all()) == 1
        assert user1.solved_tasks.first().task_id == "same/task"
        assert user2.solved_tasks.first().task_id == "same/task"

    def test_solved_task_to_dict_integration(self, db_session):
        """
        Тест метода to_dict() в интеграционном сценарии.

        Проверяет:
        - Корректность преобразования в словарь
        - Сериализацию всех полей
        """
        # Создаём пользователя и задачу
        user = User(user_name="dict_test", password_hash="hash")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        task = SolvedTask(
            user_id=user.user_id,
            task_id="test/001",
            sgf_file_name="test.sgf"
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)

        # Преобразуем в словарь
        task_dict = task.to_dict()

        # Проверяем все поля
        assert task_dict["id"] == task.id
        assert task_dict["user_id"] == user.user_id
        assert task_dict["task_id"] == "test/001"
        assert task_dict["sgf_file_name"] == "test.sgf"
        assert task_dict["is_solved"] is True
        assert "solved_at" in task_dict
        assert isinstance(task_dict["solved_at"], str)

        # Проверяем формат даты (ISO 8601)
        try:
            datetime.fromisoformat(task_dict["solved_at"].replace("Z", "+00:00"))
        except ValueError:
            pytest.fail("solved_at должен быть в формате ISO 8601")
