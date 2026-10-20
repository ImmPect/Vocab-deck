"""Сервис модуля users: профиль, изменение и удаление аккаунта, статистика, достижения.

Ничего не знает об HTTP: ошибки — исключения из app.core.errors.
"""
from datetime import UTC, date, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.errors import Conflict, Unauthorized, ValidationFailed
from app.core.security import hash_password, verify_password
from app.gamification import service as gamification
from app.learning import stats
from app.users import repository as repo
from app.users.models import User
from app.users.schemas import UpdateMe

STATS_DEFAULT_DAYS = 7  # по умолчанию — сегодня и 6 предыдущих дней
STATS_MAX_DAYS = 366


def iso_z(dt: datetime | None) -> str | None:
    """Дата и время в ISO 8601 UTC с суффиксом Z (раздел 3.1.1)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def short_user(user: User) -> dict:
    """Краткие данные пользователя для ответов /auth/register и /auth/login."""
    progress = gamification.profile_progress(user)
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "xp": user.xp,
        "level": progress["level"],
        "streak_days": progress["streak_days"],
    }


def profile(db: Session, user: User) -> dict:
    """Профиль для GET /me (раздел 3.4.1)."""
    progress = gamification.profile_progress(user)
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "timezone": user.timezone,
        "xp": user.xp,
        "level": progress["level"],
        "next_level": progress["next_level"],
        "streak_days": progress["streak_days"],
        "streak_freezes": progress["streak_freezes"],
        "inbox_count": stats.inbox_count(db, user.id, gamification.user_today(user)),
        "features": progress["features"],
        "created_at": iso_z(user.created_at),
    }


def update_me(db: Session, user: User, data: UpdateMe, current_token: str | None) -> dict:
    """PATCH /me: имя, часовой пояс, пароль. При смене пароля удаляются остальные сессии."""
    if data.new_password is not None:
        if not data.current_password:
            raise ValidationFailed(details=[{"field": "current_password",
                                             "message": "Введите текущий пароль"}])
        if not verify_password(user.password_hash, data.current_password):
            raise Unauthorized("Неверный текущий пароль", code="invalid_credentials")
        user.password_hash = hash_password(data.new_password)
        repo.delete_other_sessions(db, user.id, current_token)
    elif data.current_password is not None:
        raise ValidationFailed(details=[{"field": "new_password", "message": "Введите новый пароль"}])

    if data.name is not None:
        user.name = data.name
    if data.timezone is not None:
        user.timezone = data.timezone
    db.flush()
    return profile(db, user)


def delete_me(db: Session, user: User, password: str) -> None:
    """DELETE /me: удаление аккаунта и всех персональных данных (NFR-S-08)."""
    if not verify_password(user.password_hash, password):
        raise Unauthorized("Неверный пароль", code="invalid_credentials")
    if user.role == "admin" and repo.count_admins(db) <= 1:
        raise Conflict("Нельзя удалить последнего администратора", code="last_admin")
    repo.delete_user(db, user)


def stats_by_day(db: Session, user: User, date_from: date | None, date_to: date | None) -> dict:
    """GET /me/stats: ответы по дням в часовом поясе пользователя и итоги за период."""
    date_to = date_to or gamification.user_today(user)
    date_from = date_from or date_to - timedelta(days=STATS_DEFAULT_DAYS - 1)
    if date_from > date_to:
        raise ValidationFailed(details=[{"field": "from",
                                         "message": "Начало периода должно быть не позже конца"}])
    if (date_to - date_from).days + 1 > STATS_MAX_DAYS:
        raise ValidationFailed(details=[{"field": "to",
                                         "message": f"Период не может быть длиннее {STATS_MAX_DAYS} дней"}])

    days = stats.answers_by_day(db, user.id, date_from, date_to, user.timezone)
    totals = {
        "answers": sum(d["answers"] for d in days),
        "correct": sum(d["correct"] for d in days),
        "xp": sum(d["xp"] for d in days),
        "active_days": sum(1 for d in days if d["answers"] > 0),
        "learned_words": stats.learned_count(db, user.id),
    }
    return {"from": date_from.isoformat(), "to": date_to.isoformat(), "timezone": user.timezone,
            "days": days, "totals": totals}


def achievements(db: Session, user: User) -> dict:
    """GET /me/achievements: полученные и доступные (активные) достижения."""
    earned, available = [], []
    for a in gamification.list_achievements(db, user):
        if a["earned"]:
            earned.append({"code": a["code"], "title": a["title"], "earned_at": iso_z(a["earned_at"])})
        else:
            available.append({"code": a["code"], "title": a["title"],
                              "progress": {"current": a["progress"]["current"],
                                           "target": a["progress"]["target"]}})
    return {"earned": earned, "available": available}
