"""
Тесты для endpoints аутентификации (routes/auth.py).

Этот модуль содержит тесты для:
- Регистрации новых пользователей (POST /auth/register)
- Входа пользователей (POST /auth/login)

Категории тестов:
1. TestRegisterEndpoint - тесты endpoint регистрации
2. TestLoginEndpoint - тесты endpoint входа
3. TestAuthValidation - тесты валидации данных
4. TestAuthIntegration - интеграционные тесты полного потока

Запуск тестов:
    pytest tests/test_auth.py -v

Запуск с покрытием:
    pytest tests/test_auth.py --cov=backend/routes/auth --cov-report=term-missing
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app
from backend.database import get_db, reset_db, init_db
from backend.models.user import User
from backend.utils.security import verify_password, decode_access_token


# =============================================================================
# ФИКСТУРЫ
# =============================================================================

@pytest.fixture
def client() -> TestClient:
    """
    Создаёт тестовый клиент FastAPI для HTTP запросов.

    Returns:
        TestClient: Клиент для отправки HTTP запросов к приложению

    Example:
        def test_something(client):
            response = client.post("/auth/register", json={...})
            assert response.status_code == 201
    """
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def setup_db():
    """
    Фикстура для настройки базы данных перед каждым тестом.

    Автоматически выполняется перед каждым тестом (autouse=True):
    1. Сбрасывает базу данных (reset_db)
    2. Инициализирует базу данных заново (init_db)
    3. Создаёт чистую сессию для теста

    Это обеспечивает изоляцию тестов - каждый тест работает с чистой БД.

    Yields:
        Session: Сессия SQLAlchemy для тестов

    Example:
        def test_user_creation(setup_db):
            # БД чистая перед тестом
            # После теста БД сбрасывается
            pass
    """
    # Сбрасываем базу данных перед тестом (удаляем все таблицы)
    reset_db()

    # Инициализируем базу данных заново (создаём таблицы)
    # Это важно - модели должны быть импортированы до init_db
    from backend.models.user import User  # noqa: F401
    from backend.models.solved_task import SolvedTask  # noqa: F401
    init_db()

    # Получаем сессию базы данных
    db = next(get_db())

    try:
        yield db
    finally:
        # Закрываем сессию после теста
        db.close()


@pytest.fixture
def registered_user(client: TestClient) -> dict:
    """
    Создаёт зарегистрированного пользователя для тестов.

    Фикстура регистрирует нового пользователя через API и возвращает
    его данные для использования в других тестах.

    Args:
        client (TestClient): Тестовый клиент

    Returns:
        dict: Данные пользователя {"user_id": int, "username": str}

    Example:
        def test_something(client, registered_user):
            assert registered_user["username"] == "test_user"
    """
    response = client.post(
        "/auth/register",
        json={"username": "test_user", "password": "testpass123"}
    )
    return response.json()


# =============================================================================
# ТЕСТЫ ENDPOINT РЕГИСТРАЦИИ
# =============================================================================

class TestRegisterEndpoint:
    """Тесты для POST /auth/register endpoint."""

    def test_register_success(self, client: TestClient):
        """
        Тест успешной регистрации нового пользователя.

        Проверяет:
        - Статус код 201 Created
        - Возвращаются user_id и username
        - user_id > 0 (автоинкремент работает)
        - username совпадает с запрошенным
        """
        response = client.post(
            "/auth/register",
            json={"username": "new_user", "password": "secure123"}
        )

        # Проверяем статус код
        assert response.status_code == 201

        # Проверяем тело ответа
        data = response.json()
        assert "user_id" in data
        assert "username" in data
        assert data["username"] == "new_user"
        assert data["user_id"] > 0

    def test_register_duplicate_username(self, client: TestClient, registered_user):
        """
        Тест регистрации с существующим username.

        Проверяет:
        - Статус код 400 Bad Request
        - Возвращается сообщение об ошибке
        """
        # Пытаемся зарегистрировать пользователя с тем же именем
        response = client.post(
            "/auth/register",
            json={"username": "test_user", "password": "anotherpass1"}
        )

        # Проверяем статус код
        assert response.status_code == 400

        # Проверяем сообщение об ошибке
        data = response.json()
        assert "detail" in data
        assert "уже существует" in data["detail"]

    def test_register_password_hashed(self, client: TestClient, setup_db):
        """
        Тест хеширования пароля при регистрации.

        Проверяет:
        - Пароль хешируется перед сохранением в БД
        - Хэш можно проверить через verify_password

        Важно: этот тест проверяет, что пароль не хранится в открытом виде.
        """
        # Регистрируем пользователя
        register_response = client.post(
            "/auth/register",
            json={"username": "hash_test_user", "password": "plain_password1"}
        )
        assert register_response.status_code == 201

        # Получаем пользователя из БД
        db = setup_db
        user = db.query(User).filter(User.user_name == "hash_test_user").first()

        # Проверяем, что пользователь создан
        assert user is not None

        # Проверяем, что пароль захеширован
        assert user.password_hash != "plain_password1"
        assert user.password_hash.startswith("$2")  # bcrypt хэш начинается с $2

        # Проверяем, что verify_password работает
        assert verify_password("plain_password1", user.password_hash)
        assert not verify_password("wrong_password", user.password_hash)

    def test_register_user_not_in_db_before(self, client: TestClient, setup_db):
        """
        Тест что пользователя не было в БД до регистрации.

        Проверяет:
        - Перед регистрацией пользователя с таким именем нет
        - После регистрации пользователь появляется в БД
        """
        db = setup_db

        # Проверяем, что пользователя нет до регистрации
        user_before = db.query(User).filter(User.user_name == "before_test").first()
        assert user_before is None

        # Регистрируем пользователя
        register_response = client.post(
            "/auth/register",
            json={"username": "before_test", "password": "testpass1"}
        )
        assert register_response.status_code == 201

        # Проверяем, что пользователь появился после регистрации
        user_after = db.query(User).filter(User.user_name == "before_test").first()
        assert user_after is not None
        assert user_after.user_name == "before_test"


# =============================================================================
# ТЕСТЫ ENDPOINT ВХОДА (LOGIN)
# =============================================================================

class TestLoginEndpoint:
    """Тесты для POST /auth/login endpoint."""

    def test_login_success(self, client: TestClient, registered_user):
        """
        Тест успешного входа пользователя.

        Проверяет:
        - Статус код 200 OK
        - Возвращается access_token и token_type
        - token_type = "bearer"
        - access_token не пустой
        """
        response = client.post(
            "/auth/login",
            json={"username": "test_user", "password": "testpass123"}
        )

        # Проверяем статус код
        assert response.status_code == 200

        # Проверяем тело ответа
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 0

    def test_login_jwt_token_valid(self, client: TestClient, registered_user):
        """
        Тест валидности JWT токена после входа.

        Проверяет:
        - Токен декодируется без ошибок
        - Токен содержит user_id и username
        - Данные в токене совпадают с данными пользователя
        """
        # Входим и получаем токен
        response = client.post(
            "/auth/login",
            json={"username": "test_user", "password": "testpass123"}
        )
        token = response.json()["access_token"]

        # Декодируем токен
        token_data = decode_access_token(token)

        # Проверяем данные в токене
        assert token_data["sub"] == "test_user"
        assert token_data["user_id"] == registered_user["user_id"]
        assert "exp" in token_data  # Есть время истечения
        assert "iat" in token_data  # Есть время создания

    def test_login_wrong_password(self, client: TestClient, registered_user):
        """
        Тест входа с неверным паролем.

        Проверяет:
        - Статус код 401 Unauthorized
        - Возвращается сообщение об ошибке
        - Заголовок WWW-Authenticate присутствует
        """
        response = client.post(
            "/auth/login",
            json={"username": "test_user", "password": "wrong_password"}
        )

        # Проверяем статус код
        assert response.status_code == 401

        # Проверяем сообщение об ошибке
        data = response.json()
        assert "detail" in data
        assert "Неверное имя пользователя или пароль" in data["detail"]

        # Проверяем заголовок WWW-Authenticate
        assert "WWW-Authenticate" in response.headers
        assert "Bearer" in response.headers["WWW-Authenticate"]

    def test_login_nonexistent_user(self, client: TestClient):
        """
        Тест входа с несуществующим пользователем.

        Проверяет:
        - Статус код 401 Unauthorized
        - Возвращается общая ошибка (защита от enumeration)
        """
        response = client.post(
            "/auth/login",
            json={"username": "nonexistent_user", "password": "somepassword"}
        )

        # Проверяем статус код
        assert response.status_code == 401

        # Проверяем сообщение об ошибке
        data = response.json()
        assert "detail" in data
        assert "Неверное имя пользователя или пароль" in data["detail"]

    def test_login_empty_password(self, client: TestClient, registered_user):
        """
        Тест входа с пустым паролем.

        Проверяет:
        - Статус код 422 Validation Error (валидация Pydantic)
        """
        response = client.post(
            "/auth/login",
            json={"username": "test_user", "password": ""}
        )

        # Проверяем статус код
        assert response.status_code == 422

    def test_login_empty_username(self, client: TestClient, registered_user):
        """
        Тест входа с пустым именем пользователя.

        Проверяет:
        - Статус код 422 Validation Error (валидация Pydantic)
        """
        response = client.post(
            "/auth/login",
            json={"username": "", "password": "testpass123"}
        )

        # Проверяем статус код
        assert response.status_code == 422


# =============================================================================
# ТЕСТЫ ВАЛИДАЦИИ ДАННЫХ
# =============================================================================

class TestAuthValidation:
    """Тесты валидации данных для endpoints аутентификации."""

    def test_register_short_username(self, client: TestClient):
        """
        Тест регистрации с коротким именем (< 3 символов).

        Проверяет:
        - Статус код 422 Validation Error
        """
        response = client.post(
            "/auth/register",
            json={"username": "ab", "password": "testpass123"}
        )
        assert response.status_code == 422

    def test_register_long_username(self, client: TestClient):
        """
        Тест регистрации с длинным именем (> 50 символов).

        Проверяет:
        - Статус код 422 Validation Error
        """
        response = client.post(
            "/auth/register",
            json={"username": "a" * 51, "password": "testpass123"}
        )
        assert response.status_code == 422

    def test_register_special_chars_username(self, client: TestClient):
        """
        Тест регистрации с недопустимыми символами в имени.

        Проверяет:
        - Статус код 422 Validation Error
        """
        response = client.post(
            "/auth/register",
            json={"username": "user@name!", "password": "testpass123"}
        )
        assert response.status_code == 422

    def test_register_short_password(self, client: TestClient):
        """
        Тест регистрации с коротким паролем (< 5 символов).

        Проверяет:
        - Статус код 422 Validation Error
        """
        response = client.post(
            "/auth/register",
            json={"username": "test_user", "password": "1234"}
        )
        assert response.status_code == 422

    def test_register_missing_username(self, client: TestClient):
        """
        Тест регистрации без username.

        Проверяет:
        - Статус код 422 Validation Error
        """
        response = client.post(
            "/auth/register",
            json={"password": "testpass123"}
        )
        assert response.status_code == 422

    def test_register_missing_password(self, client: TestClient):
        """
        Тест регистрации без password.

        Проверяет:
        - Статус код 422 Validation Error
        """
        response = client.post(
            "/auth/register",
            json={"username": "test_user"}
        )
        assert response.status_code == 422

    def test_login_missing_username(self, client: TestClient):
        """
        Тест входа без username.

        Проверяет:
        - Статус код 422 Validation Error
        """
        response = client.post(
            "/auth/login",
            json={"password": "testpass123"}
        )
        assert response.status_code == 422

    def test_login_missing_password(self, client: TestClient):
        """
        Тест входа без password.

        Проверяет:
        - Статус код 422 Validation Error
        """
        response = client.post(
            "/auth/login",
            json={"username": "test_user"}
        )
        assert response.status_code == 422


# =============================================================================
# ИНТЕГРАЦИОННЫЕ ТЕСТЫ
# =============================================================================

class TestAuthIntegration:
    """Интеграционные тесты полного потока аутентификации."""

    def test_full_auth_flow(self, client: TestClient, setup_db):
        """
        Тест полного потока: регистрация → вход → проверка токена.

        Проверяет:
        - Регистрация нового пользователя
        - Вход с полученными учётными данными
        - Валидность JWT токена
        - Данные в токене соответствуют пользователю
        """
        # Шаг 1: Регистрация
        register_response = client.post(
            "/auth/register",
            json={"username": "flow_test_user", "password": "flowpass123"}
        )
        assert register_response.status_code == 201
        user_data = register_response.json()
        assert user_data["username"] == "flow_test_user"

        # Шаг 2: Вход
        login_response = client.post(
            "/auth/login",
            json={"username": "flow_test_user", "password": "flowpass123"}
        )
        assert login_response.status_code == 200
        token_data = login_response.json()
        assert "access_token" in token_data

        # Шаг 3: Проверка токена
        decoded = decode_access_token(token_data["access_token"])
        assert decoded["sub"] == "flow_test_user"
        assert decoded["user_id"] == user_data["user_id"]

    def test_multiple_users_independent(self, client: TestClient, setup_db):
        """
        Тест независимости данных нескольких пользователей.

        Проверяет:
        - Можно зарегистрировать нескольких пользователей
        - Каждый может войти со своим паролем
        - Токены разных пользователей разные
        """
        # Регистрируем двух пользователей
        user1 = client.post(
            "/auth/register",
            json={"username": "user_one", "password": "pass111"}
        ).json()

        user2 = client.post(
            "/auth/register",
            json={"username": "user_two", "password": "pass222"}
        ).json()

        # Входим как первый пользователь
        token1 = client.post(
            "/auth/login",
            json={"username": "user_one", "password": "pass111"}
        ).json()["access_token"]

        # Входим как второй пользователь
        token2 = client.post(
            "/auth/login",
            json={"username": "user_two", "password": "pass222"}
        ).json()["access_token"]

        # Проверяем, что токены разные
        assert token1 != token2

        # Проверяем данные в токенах
        decoded1 = decode_access_token(token1)
        decoded2 = decode_access_token(token2)

        assert decoded1["sub"] == "user_one"
        assert decoded2["sub"] == "user_two"
        assert decoded1["user_id"] != decoded2["user_id"]

    def test_register_login_change_password(self, client: TestClient, setup_db):
        """
        Тест: регистрация → вход → смена пароля → вход со старым паролем.

        Проверяет:
        - Регистрация и вход работают
        - После смены пароля старый пароль не работает
        - Новый пароль работает
        """
        from backend.services.auth import (
            get_user_by_username,
            change_user_password,
        )

        # Регистрируем пользователя
        register_response = client.post(
            "/auth/register",
            json={"username": "change_pass_user", "password": "old_pass1"}
        )
        assert register_response.status_code == 201

        # Входим со старым паролем
        login_old = client.post(
            "/auth/login",
            json={"username": "change_pass_user", "password": "old_pass1"}
        )
        assert login_old.status_code == 200

        # Меняем пароль через сервис (напрямую в БД)
        db = setup_db
        user = get_user_by_username(db, "change_pass_user")
        assert user is not None
        change_user_password(db, user, "old_pass1", "new_pass1")

        # Вход со старым паролем должен вернуть ошибку
        login_old_after = client.post(
            "/auth/login",
            json={"username": "change_pass_user", "password": "old_pass1"}
        )
        assert login_old_after.status_code == 401

        # Вход с новым паролем должен работать
        login_new = client.post(
            "/auth/login",
            json={"username": "change_pass_user", "password": "new_pass1"}
        )
        assert login_new.status_code == 200

    def test_db_cleanup_between_tests(self, client: TestClient, setup_db):
        """
        Тест очистки БД между тестами.

        Проверяет:
        - Фикстура setup_db корректно очищает БД
        - Каждый тест начинается с чистой БД
        """
        db = setup_db

        # Проверяем, что БД пустая (пользователь из предыдущего теста удалён)
        user_count = db.query(User).count()
        assert user_count == 0

        # Регистрируем пользователя
        register_response = client.post(
            "/auth/register",
            json={"username": "cleanup_test_user", "password": "testpass1"}
        )
        assert register_response.status_code == 201

        # Проверяем, что пользователь создан
        user_count = db.query(User).count()
        assert user_count == 1

        # После завершения этого теста БД будет очищена фикстурой

    def test_concurrent_registration_different_users(self, client: TestClient, setup_db):
        """
        Тест одновременной регистрации разных пользователей.

        Проверяет:
        - Можно зарегистрировать много пользователей подряд
        - У всех разные user_id
        - Все могут войти
        """
        users = []

        # Регистрируем 5 пользователей
        for i in range(5):
            response = client.post(
                "/auth/register",
                json={"username": f"user_{i}", "password": f"pass_{i}"}
            )
            assert response.status_code == 201
            users.append(response.json())

        # Проверяем, что у всех разные ID
        user_ids = [u["user_id"] for u in users]
        assert len(set(user_ids)) == 5  # Все ID уникальны

        # Проверяем, что все могут войти
        for i in range(5):
            login_response = client.post(
                "/auth/login",
                json={"username": f"user_{i}", "password": f"pass_{i}"}
            )
            assert login_response.status_code == 200
            assert "access_token" in login_response.json()
