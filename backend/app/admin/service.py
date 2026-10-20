"""Сервис модуля admin: поиск пользователей по почте (раздел 3.8.5 ПР3).

Слова и отделы админка изменяет через сервисы words и decks; здесь — только
чтение пользователей, поэтому модуль users не зависит от админки.
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ValidationFailed
from app.core.responses import Page
from app.gamification.rules import level_for
from app.users.models import User
from app.words.service import iso


def user_out(u: User) -> dict:
    """Карточка пользователя для админки; password_hash и failed_logins не выдаются."""
    level = level_for(u.xp)
    return {"id": u.id, "name": u.name, "email": u.email, "role": u.role, "xp": u.xp,
            "level": {"code": level["code"], "title": level["title"]},
            "locked_until": iso(u.locked_until), "created_at": iso(u.created_at)}


def search_users(db: Session, email: str | None, page: Page) -> tuple[list[dict], dict]:
    email = (email or "").strip()
    if len(email) < 3:
        raise ValidationFailed(details=[{"field": "email", "message": "Введите не менее 3 символов почты"}])
    stmt = select(User).where(func.lower(User.email).contains(email.lower(), autoescape=True))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    users = db.scalars(stmt.order_by(User.email).offset(page.offset).limit(page.limit))
    return [user_out(u) for u in users], page.meta(total)
