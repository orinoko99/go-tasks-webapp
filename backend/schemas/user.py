"""
Pydantic схемы для пользователей и аутентификации.

Этот модуль содержит схемы валидации данных для:
- Регистрации нового пользователя
- Входа пользователя (login)
- Ответа с данными пользователя
- Ответа с JWT токеном

Все схемы используют Pydantic v2 синтаксис.
"""

from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict


class UserCreate(BaseModel):
    """
    Схема для создания нового пользователя (регистрация).
    
    Используется при регистрации пользователя через эндпоинт /auth/register.
    Проверяет, что имя пользователя и пароль соответствуют требованиям.
    """
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Имя пользователя (от 3 до 50 символов)"
    )
    password: str = Field(
        ...,
        min_length=5,
        max_length=72,
        description="Пароль (от 5 до 72 символов)"
    )
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        """
        Валидация имени пользователя.
        
        Проверяет, что имя содержит только допустимые символы
        (буквы, цифры, подчёркивание, дефис).
        """
        # Сначала обрезаем пробелы
        v = v.strip()
        if not v:
            raise ValueError('Имя пользователя не может быть пустым')
        # Разрешаем буквы, цифры, подчёркивание и дефис
        allowed_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-')
        if not all(c in allowed_chars for c in v):
            raise ValueError(
                'Имя пользователя может содержать только буквы, цифры, '
                'подчёркивание и дефис'
            )
        return v
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """
        Валидация пароля.
        
        Проверяет, что пароль содержит хотя бы одну букву и одну цифру.
        """
        if not any(c.isalpha() for c in v):
            raise ValueError('Пароль должен содержать хотя бы одну букву')
        if not any(c.isdigit() for c in v):
            raise ValueError('Пароль должен содержать хотя бы одну цифру')
        return v


class UserLogin(BaseModel):
    """
    Схема для входа пользователя (login).
    
    Используется при аутентификации через эндпоинт /auth/login.
    Содержит имя пользователя и пароль для проверки.
    """
    username: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Имя пользователя"
    )
    password: str = Field(
        ...,
        min_length=1,
        max_length=72,
        description="Пароль"
    )
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Валидация имени пользователя при входе."""
        if not v.strip():
            raise ValueError('Имя пользователя не может быть пустым')
        return v.strip()


class UserResponse(BaseModel):
    """
    Схема ответа с данными пользователя.
    
    Используется для возврата информации о пользователе
    после успешной регистрации или входа.
    Не содержит чувствительных данных (пароля).
    """
    user_id: int = Field(..., description="Уникальный идентификатор пользователя")
    username: str = Field(..., description="Имя пользователя")
    
    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """
    Схема ответа с JWT токеном.
    
    Используется для возврата access_token после успешной аутентификации.
    """
    access_token: str = Field(..., description="JWT токен доступа")
    token_type: str = Field(default="bearer", description="Тип токена")
    
    model_config = ConfigDict(from_attributes=True)


class TokenData(BaseModel):
    """
    Схема для данных внутри JWT токена.
    
    Используется для декодирования и валидации данных токена.
    """
    user_id: int = Field(..., description="ID пользователя")
    username: str = Field(..., description="Имя пользователя")
    exp: datetime = Field(..., description="Время истечения токена")
    iat: datetime = Field(..., description="Время создания токена")
