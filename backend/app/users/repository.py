"""Запросы к таблицам users и sessions (SQLAlchemy).

Используется сервисами users и auth; другие модули обращаются к пользователям
только через сервисы, а не через этот файл.
"""
from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.users.models import User, UserSession


def get_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def email_exists(db: Session, email: str) -> bool:
    return db.scalar(select(func.count()).select_from(User).where(User.email == email)) > 0


def add_user(db: Session, user: User) -> User:
    db.add(user)
    db.flush()  # получить id в текущей транзакции
    return user


def delete_user(db: Session, user: User) -> None:
    """Удаляет пользователя; связанные строки удаляет СУБД (ON DELETE CASCADE / SET NULL)."""
    db.delete(user)
    db.flush()


def count_admins(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(User).where(User.role == "admin")) or 0


def add_session(db: Session, token: str, user_id: int, expires_at: datetime) -> UserSession:
    sess = UserSession(id=token, user_id=user_id, expires_at=expires_at)
    db.add(sess)
    db.flush()
    return sess


def delete_session(db: Session, token: str) -> None:
    db.execute(delete(UserSession).where(UserSession.id == token))


def delete_other_sessions(db: Session, user_id: int, keep_token: str | None) -> None:
    """Удаляет все сессии пользователя, кроме текущей (смена пароля)."""
    stmt = delete(UserSession).where(UserSession.user_id == user_id)
    if keep_token:
        stmt = stmt.where(UserSession.id != keep_token)
    db.execute(stmt)
