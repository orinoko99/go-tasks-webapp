"""
Модуль подключения к базе данных и управления сессиями.

Использует SQLite с режимом WAL для поддержки конкурентного доступа.
Предоставляет движок, сессию фабрики и базовый класс для моделей.
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from typing import Generator

# Путь к файлу базы данных
DATABASE_URL = "sqlite:///./data/database.db"

# Создание движка SQLite с настройками для конкурентного доступа
# pool_check_same_thread=False позволяет использовать соединение в разных потоках
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
    echo=False  # Логирование SQL запросов (отключено в продакшене)
)

# Включение режима WAL для улучшения конкурентного доступа
# Выполняется при каждом подключении
def enable_wal(dbapi_connection, connection_record):
    """Включает режим WAL для SQLite соединения."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()

event.listen(engine, "connect", enable_wal)

# Фабрика сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Базовый класс для моделей
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Зависимость для получения сессии базы данных.
    
    Используется в FastAPI зависимостях для автоматического
    открытия и закрытия сессии для каждого запроса.
    
    Yields:
        Session: Сессия SQLAlchemy
        
    Example:
        ```python
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            return db.query(User).all()
        ```
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Инициализация базы данных.
    
    Создаёт все таблицы согласно определённым моделям.
    Вызывается при старте приложения.
    """
    Base.metadata.create_all(bind=engine)


def reset_db() -> None:
    """
    Сброс базы данных.
    
    Удаляет все таблицы. Используется только в тестировании.
    """
    Base.metadata.drop_all(bind=engine)
