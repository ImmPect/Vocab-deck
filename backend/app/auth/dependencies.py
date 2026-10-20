"""Зависимости FastAPI для проверки сессии и роли (раздел 2.6 ПР3).

Подключаются к роутерам: get_current_user — для пользователя,
get_optional_user — для эндпоинтов, доступных гостю, require_admin — для admin.
"""
from fastapi import Cookie, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db, utcnow
from app.core.errors import Forbidden, Unauthorized
from app.users.models import User, UserSession

SESSION_COOKIE = "session_id"


def get_optional_user(session_id: str | None = Cookie(default=None, alias=SESSION_COOKIE),
                      db: Session = Depends(get_db)) -> User | None:
    if not session_id:
        return None
    sess = db.get(UserSession, session_id)
    if sess is None or sess.expires_at <= utcnow():
        return None
    return sess.user


def get_current_user(user: User | None = Depends(get_optional_user)) -> User:
    if user is None:
        raise Unauthorized()
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Роль проверяется на каждом запросе (NFR-S-07)."""
    if user.role != "admin":
        raise Forbidden()
    return user
