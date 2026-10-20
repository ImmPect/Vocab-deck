"""Подключение к базе данных и общие типы столбцов.

Основная СУБД — PostgreSQL. Для локальной разработки и тестов поддерживается
SQLite: типы JSONB и BIGSERIAL подменяются совместимыми вариантами.
"""
from collections.abc import Iterator
from datetime import UTC, datetime

from sqlalchemy import JSON, BigInteger, DateTime, Integer, create_engine, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.types import TypeDecorator

from app.core.config import settings

# BIGSERIAL в PostgreSQL; в SQLite автоинкремент работает только у INTEGER PRIMARY KEY
BigId = BigInteger().with_variant(Integer, "sqlite")
# JSONB в PostgreSQL, JSON (текст) в SQLite
JsonB = JSON().with_variant(JSONB(), "postgresql")


def utcnow() -> datetime:
    return datetime.now(UTC)


class UTCDateTime(TypeDecorator):
    """TIMESTAMPTZ. Всегда возвращает aware-datetime в UTC (SQLite хранит без пояса)."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value


class Base(DeclarativeBase):
    pass


def make_engine(url: str):
    kwargs = {}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        kwargs["pool_pre_ping"] = True
    eng = create_engine(url, **kwargs)
    if url.startswith("sqlite"):
        @event.listens_for(eng, "connect")
        def _fk_on(dbapi_conn, _):  # в SQLite внешние ключи по умолчанию выключены
            dbapi_conn.execute("PRAGMA foreign_keys=ON")
    return eng


engine = make_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """Зависимость FastAPI: одна сессия БД (одна транзакция) на запрос."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
