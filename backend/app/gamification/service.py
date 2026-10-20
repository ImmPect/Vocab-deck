"""Сервис геймификации: опыт, серия дней, достижения.

Внутренний модуль без эндпоинтов. Вызывается из learning (ответы и итоги раунда),
auth (перенос гостевого прогресса) и users (профиль, список достижений).
Правила — в rules.py; здесь только применение их к пользователю и БД.
"""
from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.db import utcnow
from app.gamification import rules
from app.gamification.models import Achievement, UserAchievement
from app.users.models import User


def user_today(user: User | None, at: datetime | None = None) -> date:
    """Календарная дата пользователя по его часовому поясу (гость — Europe/Moscow)."""
    tz = ZoneInfo(user.timezone if user else "Europe/Moscow")
    return (at or utcnow()).astimezone(tz).date()


def award(user: User, xp: int) -> None:
    """Начисляет опыт (кэш users.xp; источник истины — answer_events.xp_awarded)."""
    if xp:
        user.xp += xp


def register_activity(user: User, day: date) -> None:
    """Учитывает проверяемый ответ в день day: серия дней и заморозки (п. 3.8 ТЗ)."""
    state = rules.update_streak(
        rules.StreakState(user.streak_days, user.streak_freezes, user.last_active_date), day)
    user.streak_days, user.streak_freezes, user.last_active_date = (
        state.streak_days, state.streak_freezes, state.last_active_date)


def profile_progress(user: User) -> dict:
    """Должность, следующая должность, открытые функции и актуальная серия."""
    today = user_today(user)
    return {
        "level": rules.level_for(user.xp),
        "next_level": rules.next_level_for(user.xp),
        "features": rules.features_for(user.xp),
        "streak_days": rules.current_streak(
            rules.StreakState(user.streak_days, user.streak_freezes, user.last_active_date), today),
        "streak_freezes": user.streak_freezes,
    }


def _metrics(db: Session, user: User, extra: dict | None = None) -> dict:
    """Показатели для проверки условий достижений."""
    from app.learning import stats  # локальный импорт: learning зависит от gamification, не наоборот

    m = {
        "xp": user.xp,
        "streak_days": user.streak_days,
        "learned_words": stats.learned_count(db, user.id),
        "rounds_finished": stats.rounds_finished(db, user.id),
    }
    m.update(extra or {})
    return m


def _satisfied(condition: dict, metrics: dict) -> bool:
    return all(metrics.get(key, 0) >= need for key, need in condition.items())


def check_achievements(db: Session, user: User) -> list[dict]:
    """Выдаёт новые достижения, условия которых выполнены. Возвращает только новые."""
    have = set(db.scalars(select(UserAchievement.achievement_id).where(UserAchievement.user_id == user.id)))
    candidates = db.scalars(select(Achievement).where(Achievement.is_active.is_(True))).all()
    candidates = [a for a in candidates if a.id not in have]
    if not candidates:
        return []
    metrics = _metrics(db, user)
    earned = []
    for a in candidates:
        if _satisfied(a.condition, metrics):
            db.add(UserAchievement(user_id=user.id, achievement_id=a.id))
            earned.append({"code": a.code, "title": a.title})
    db.flush()
    return earned


def list_achievements(db: Session, user: User) -> list[dict]:
    """Все активные достижения с признаком получения и прогрессом (GET /me/achievements)."""
    earned = dict(db.execute(
        select(UserAchievement.achievement_id, UserAchievement.earned_at)
        .where(UserAchievement.user_id == user.id)).all())
    metrics = _metrics(db, user)
    out = []
    for a in db.scalars(select(Achievement).where(Achievement.is_active.is_(True)).order_by(Achievement.id)):
        key, need = next(iter(a.condition.items()))
        out.append({
            "code": a.code,
            "title": a.title,
            "earned": a.id in earned,
            "earned_at": earned.get(a.id),
            "progress": {"metric": key, "current": min(metrics.get(key, 0), need), "target": need},
        })
    return out


def count_earned(db: Session, user_id: int) -> int:
    return db.scalar(select(func.count()).select_from(UserAchievement)
                     .where(UserAchievement.user_id == user_id)) or 0
