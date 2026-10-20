"""Доступ к БД модуля learning: прогресс, журнал ответов, раунды, входящие.

Только запросы SQLAlchemy, без правил игры и без HTTP.
"""
import uuid
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.decks.models import Deck
from app.gamification.models import Achievement, UserAchievement
from app.gamification.rules import GAME_MODES
from app.learning.models import AnswerEvent, Round, UserWordProgress
from app.words.models import Word


def add(db: Session, obj):
    """Добавляет объект и сразу отправляет INSERT (autoflush выключен)."""
    db.add(obj)
    db.flush()
    return obj


# ---------- колоды и слова ----------

def get_deck(db: Session, deck_id: int) -> Deck | None:
    return db.get(Deck, deck_id)


def get_word(db: Session, word_id: int) -> Word | None:
    return db.get(Word, word_id)


def published_words(db: Session, deck_id: int) -> list[Word]:
    return list(db.scalars(select(Word).where(Word.deck_id == deck_id, Word.status == "published")
                           .order_by(Word.id)))


# ---------- прогресс ----------

def get_progress(db: Session, user_id: int, word_id: int, direction: str) -> UserWordProgress | None:
    return db.get(UserWordProgress, (user_id, word_id, direction))


def progress_for_words(db: Session, user_id: int, word_ids: list[int],
                       direction: str) -> dict[int, UserWordProgress]:
    if not word_ids:
        return {}
    rows = db.scalars(select(UserWordProgress).where(
        UserWordProgress.user_id == user_id, UserWordProgress.direction == direction,
        UserWordProgress.word_id.in_(word_ids)))
    return {p.word_id: p for p in rows}


def inbox_page(db: Session, user_id: int, today: date, direction: str | None,
               offset: int, limit: int) -> tuple[list[tuple[UserWordProgress, Word, Deck]], int]:
    """Слова со сроком повтора не позже today (без архивных): сначала самые просроченные, затем по ящику."""
    conds = [UserWordProgress.user_id == user_id, UserWordProgress.next_review_at <= today,
             Word.status != "archived"]
    if direction:
        conds.append(UserWordProgress.direction == direction)
    base = (select(UserWordProgress, Word, Deck)
            .join(Word, Word.id == UserWordProgress.word_id)
            .join(Deck, Deck.id == Word.deck_id)
            .where(*conds))
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.execute(base.order_by(UserWordProgress.next_review_at, UserWordProgress.box,
                                    UserWordProgress.word_id, UserWordProgress.direction)
                      .offset(offset).limit(limit)).all()
    return [tuple(r) for r in rows], total


# ---------- журнал ответов ----------

def get_event(db: Session, client_event_id: uuid.UUID) -> AnswerEvent | None:
    return db.scalar(select(AnswerEvent).where(AnswerEvent.client_event_id == client_event_id))


def has_correct_game_answer(db: Session, user_id: int, word_id: int, start: datetime, end: datetime) -> bool:
    """Был ли в интервале [start, end) верный ответ на слово в мини-игре (правило «тот же день»)."""
    return db.scalar(select(AnswerEvent.id).where(
        AnswerEvent.user_id == user_id, AnswerEvent.word_id == word_id, AnswerEvent.is_correct.is_(True),
        AnswerEvent.mode.in_(GAME_MODES), AnswerEvent.answered_at >= start, AnswerEvent.answered_at < end,
    ).limit(1)) is not None


# ---------- раунды ----------

def get_round(db: Session, round_id: uuid.UUID, *, lock: bool = False) -> Round | None:
    """lock=True — SELECT ... FOR UPDATE в PostgreSQL (в SQLite игнорируется)."""
    stmt = select(Round).where(Round.id == round_id)
    if lock:
        stmt = stmt.with_for_update()
    return db.scalar(stmt)


def round_exists(db: Session, round_id: uuid.UUID) -> bool:
    return db.scalar(select(Round.id).where(Round.id == round_id)) is not None


# ---------- достижения ----------

def achievements_earned_between(db: Session, user_id: int, start: datetime, end: datetime) -> list[dict]:
    rows = db.execute(select(Achievement.code, Achievement.title)
                      .join(UserAchievement, UserAchievement.achievement_id == Achievement.id)
                      .where(UserAchievement.user_id == user_id, UserAchievement.earned_at >= start,
                             UserAchievement.earned_at <= end)
                      .order_by(Achievement.id)).all()
    return [{"code": c, "title": t} for c, t in rows]
