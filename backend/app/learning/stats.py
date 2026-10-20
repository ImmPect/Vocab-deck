"""Запросы только на чтение к прогрессу и журналу ответов.

Публичный интерфейс модуля learning для других модулей (users, decks,
gamification): они не обращаются к таблицам learning напрямую.
"""
from collections import defaultdict
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.learning.models import AnswerEvent, Round, UserWordProgress
from app.words.models import Word


def inbox_count(db: Session, user_id: int, today: date) -> int:
    """Число слов, срок повтора которых наступил (без архивных)."""
    return db.scalar(
        select(func.count()).select_from(UserWordProgress)
        .join(Word, Word.id == UserWordProgress.word_id)
        .where(UserWordProgress.user_id == user_id, UserWordProgress.next_review_at <= today,
               Word.status != "archived")) or 0


def learned_count(db: Session, user_id: int) -> int:
    """Число выученных слов (по направлению EN→RU)."""
    return db.scalar(select(func.count()).select_from(UserWordProgress).where(
        UserWordProgress.user_id == user_id, UserWordProgress.direction == "en_ru",
        UserWordProgress.learned.is_(True))) or 0


def rounds_finished(db: Session, user_id: int) -> int:
    return db.scalar(select(func.count()).select_from(Round).where(
        Round.user_id == user_id, Round.finished_at.is_not(None))) or 0


def deck_progress(db: Session, user_id: int | None, deck_ids: list[int],
                  direction: str = "en_ru") -> dict[int, dict]:
    """Прогресс по колодам: {deck_id: {"total", "learned", "in_progress", "new"}}.

    total — опубликованные слова; learned — выученные; in_progress — в ящиках, но не выученные;
    new — без прогресса. Для гостя (user_id=None) все слова считаются новыми.
    """
    result = {d: {"total": 0, "learned": 0, "in_progress": 0, "new": 0} for d in deck_ids}
    if not deck_ids:
        return result
    totals = db.execute(
        select(Word.deck_id, func.count()).where(Word.deck_id.in_(deck_ids), Word.status == "published")
        .group_by(Word.deck_id)).all()
    for deck_id, total in totals:
        result[deck_id]["total"] = total
    if user_id is not None:
        rows = db.execute(
            select(Word.deck_id,
                   func.sum(case((UserWordProgress.learned.is_(True), 1), else_=0)),
                   func.sum(case((UserWordProgress.learned.is_(False), 1), else_=0)))
            .join(UserWordProgress, UserWordProgress.word_id == Word.id)
            .where(Word.deck_id.in_(deck_ids), Word.status == "published",
                   UserWordProgress.user_id == user_id, UserWordProgress.direction == direction)
            .group_by(Word.deck_id)).all()
        for deck_id, learned, in_progress in rows:
            result[deck_id]["learned"] = int(learned or 0)
            result[deck_id]["in_progress"] = int(in_progress or 0)
    for r in result.values():
        r["new"] = max(r["total"] - r["learned"] - r["in_progress"], 0)
    return result


def learned_in_deck(db: Session, user_id: int, deck_id: int) -> int:
    return deck_progress(db, user_id, [deck_id])[deck_id]["learned"]


def answers_by_day(db: Session, user_id: int, date_from: date, date_to: date, tz_name: str) -> list[dict]:
    """Проверяемые ответы (мини-игры) по дням в часовом поясе пользователя (GET /me/stats).

    Группировка выполняется в Python, чтобы одинаково работать в PostgreSQL и SQLite.
    """
    tz = ZoneInfo(tz_name)
    start = datetime.combine(date_from, datetime.min.time(), tz)
    end = datetime.combine(date_to + timedelta(days=1), datetime.min.time(), tz)
    rows = db.execute(
        select(AnswerEvent.created_at, AnswerEvent.is_correct, AnswerEvent.xp_awarded)
        .where(AnswerEvent.user_id == user_id, AnswerEvent.created_at >= start, AnswerEvent.created_at < end,
               AnswerEvent.mode.in_(("deadline", "dictation")))  # только проверяемые ответы
    ).all()
    days: dict[date, dict] = defaultdict(lambda: {"answers": 0, "correct": 0, "xp": 0})
    for created_at, is_correct, xp in rows:
        d = created_at.astimezone(tz).date()
        days[d]["answers"] += 1
        days[d]["correct"] += int(is_correct)
        days[d]["xp"] += xp
    out, d = [], date_from
    while d <= date_to:
        out.append({"date": d.isoformat(), **days.get(d, {"answers": 0, "correct": 0, "xp": 0})})
        d += timedelta(days=1)
    return out
