"""
Маршруты аутентификации для системы Go Problems Trainer.

Этот модуль содержит HTTP endpoints для:
- Регистрации новых пользователей (POST /auth/register)
- Входа пользователей и получения JWT токена (POST /auth/login)

Endpoints используют:
- Сервисы аутентификации из backend.services.auth
- Схемы Pydantic из backend.schemas.user
- Безопасность из backend.utils.security

Все endpoints возвращают данные в формате JSON.
"""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.user import UserCreate, UserLogin, UserResponse, TokenResponse
from backend.services.auth import (
    register_user,
    authenticate_user,
    UserAlreadyExistsError,
    InvalidCredentialsError,
)


# =============================================================================
# РОУТЕР
# =============================================================================

# Создаём роутер для всех endpoints аутентификации
# Префикс "/auth" добавляется ко всем маршрутам автоматически
# Теги используются для группировки в документации OpenAPI/Swagger
router = APIRouter(prefix="/auth", tags=["Authentication"])


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация нового пользователя",
    description=(
        "Регистрирует нового пользователя в системе.\n\n"
        "Требования к данным:\n"
        "- **username**: 3-20 символов, только буквы, цифры, подчёркивания\n"
        "- **password**: минимум 5 символов\n\n"
        "Возвращает данные созданного пользователя (без пароля)."
    ),
    responses={
        201: {"description": "Пользователь успешно зарегистрирован", "model": UserResponse},
        400: {"description": "Пользователь с таким именем уже существует"},
        422: {"description": "Ошибка валидации данных"},
    }
)
def register_endpoint(user_data: UserCreate) -> UserResponse:
    """
    Endpoint регистрации нового пользователя.

    Принимает данные пользователя (имя и пароль), создаёт нового пользователя
    в базе данных и возвращает данные созданного пользователя.

    Args:
        user_data (UserCreate): Данные пользователя из тела запроса
            - username: str - Имя пользователя (3-20 символов)
            - password: str - Пароль (минимум 5 символов)

    Returns:
        UserResponse: Данные созданного пользователя
            - user_id: int - Уникальный идентификатор пользователя
            - username: str - Имя пользователя

    Raises:
        HTTPException(status=400): Если пользователь с таким именем уже существует
        HTTPException(status=422): Если данные не прошли валидацию Pydantic

    Example запроса:
        POST /auth/register
        Content-Type: application/json

        {
            "username": "new_user",
            "password": "secure123"
        }

    Example ответа (201 Created):
        {
            "user_id": 42,
            "username": "new_user"
        }

    Example ответа (400 Bad Request):
        {
            "detail": "Пользователь с именем 'new_user' уже существует"
        }

    Security Note:
        - Пароль хешируется перед сохранением в БД
        - Пароль никогда не возвращается в ответе
        - Имя пользователя должно быть уникальным
    """
    # Получаем сессию базы данных
    # get_db() создаёт контекстный менеджер, который автоматически
    # закрывает сессию после завершения запроса
    db = next(get_db())

    try:
        # Регистрируем нового пользователя через сервис
        # register_user выбрасывает UserAlreadyExistsError если пользователь существует
        new_user = register_user(db=db, user_data=user_data)

        # Возвращаем данные созданного пользователя
        # UserResponse автоматически конвертирует модель SQLAlchemy в Pydantic схему
        return UserResponse(
            user_id=new_user.user_id,
            username=new_user.user_name
        )

    except UserAlreadyExistsError as e:
        # Пользователь уже существует - возвращаем HTTP 400
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    finally:
        # Закрываем сессию базы данных
        # Это важно для освобождения ресурсов и предотвращения утечек соединений
        db.close()


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Вход пользователя",
    description=(
        "Аутентифицирует пользователя по имени и паролю.\n\n"
        "Возвращает JWT access токен для доступа к защищённым endpoints.\n\n"
        "Токен действителен в течение 30 минут (настраивается в config)."
    ),
    responses={
        200: {"description": "Вход выполнен успешно", "model": TokenResponse},
        401: {"description": "Неверное имя пользователя или пароль"},
        422: {"description": "Ошибка валидации данных"},
    }
)
def login_endpoint(credentials: UserLogin) -> TokenResponse:
    """
    Endpoint входа пользователя в систему.

    Принимает имя пользователя и пароль, проверяет учётные данные
    и возвращает JWT access токен для доступа к защищённым ресурсам.

    Args:
        credentials (UserLogin): Учётные данные из тела запроса
            - username: str - Имя пользователя
            - password: str - Пароль

    Returns:
        TokenResponse: Данные для доступа
            - access_token: str - JWT токен для авторизации
            - token_type: str - Тип токена (всегда "bearer")

    Raises:
        HTTPException(status=401): Если имя пользователя или пароль неверны
        HTTPException(status=422): Если данные не прошли валидацию Pydantic

    Example запроса:
        POST /auth/login
        Content-Type: application/json

        {
            "username": "john_doe",
            "password": "password123"
        }

    Example ответа (200 OK):
        {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "token_type": "bearer"
        }

    Example ответа (401 Unauthorized):
        {
            "detail": "Неверное имя пользователя или пароль"
        }

    Security Note:
        - Используется постоянное по времени сравнение паролей
        - JWT токен содержит user_id и username
        - Токен нужно передавать в заголовке Authorization: Bearer <token>
        - Неверные учётные данные возвращают общую ошибку (защита от enumeration)

    Usage:
        После получения токена его нужно передавать в заголовке запросов:
        ```
        Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
        ```
    """
    # Получаем сессию базы данных
    db = next(get_db())

    try:
        # Аутентифицируем пользователя через сервис
        # authenticate_user возвращает кортеж (user, token) или (None, error_message)
        user, token = authenticate_user(
            db=db,
            username=credentials.username,
            password=credentials.password
        )

        # Если пользователь не найден или пароль неверный
        if user is None:
            # Возвращаем HTTP 401 Unauthorized
            # token содержит сообщение об ошибке от authenticate_user
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=token,
                # Заголовок для WWW-Authenticate (стандарт OAuth2)
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Возвращаем JWT токен
        # token_type: "bearer" - стандартный тип токена для OAuth2
        return TokenResponse(
            access_token=token,
            token_type="bearer"
        )

    finally:
        # Закрываем сессию базы данных
        db.close()
