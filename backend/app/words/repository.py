"""Запросы к таблице words.

Прогресс по отдельным словам читается из user_word_progress только на чтение:
в публичном интерфейсе learning (stats.py) нет функции «прогресс по списку слов».
"""
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.decks.models import Deck
from app.learning.models import UserWordProgress
from app.users.models import User
from app.words.models import Word


def get(db: Session, word_id: int) -> Word | None:
    return db.get(Word, word_id)


def add(db: Session, word: Word) -> Word:
    db.add(word)
    db.flush()
    return word


def delete(db: Session, word: Word) -> None:
    db.delete(word)
    db.flush()


def find_duplicate(db: Session, deck_id: int, en: str, exclude_id: int | None = None) -> int | None:
    """id слова с тем же en (без учёта регистра) в колоде или None."""
    stmt = select(Word.id).where(Word.deck_id == deck_id, func.lower(Word.en) == en.lower())
    if exclude_id is not None:
        stmt = stmt.where(Word.id != exclude_id)
    return db.scalar(stmt.limit(1))


def existing_en(db: Session, deck_id: int) -> set[str]:
    """Все en колоды в нижнем регистре (проверка дубликатов при импорте)."""
    return {en.lower() for en in db.scalars(select(Word.en).where(Word.deck_id == deck_id))}


def count_in_deck(db: Session, deck_id: int) -> int:
    return db.scalar(select(func.count()).select_from(Word).where(Word.deck_id == deck_id)) or 0


def _search(stmt, q: str | None):
    if q:
        needle = q.lower()
        stmt = stmt.where(or_(func.lower(Word.en).contains(needle, autoescape=True),
                              func.lower(Word.ru).contains(needle, autoescape=True)))
    return stmt


def list_published(db: Session, deck_id: int, q: str | None, offset: int, limit: int) -> tuple[list[Word], int]:
    """Опубликованные слова колоды, сортировка по en."""
    stmt = _search(select(Word).where(Word.deck_id == deck_id, Word.status == "published"), q)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = list(db.scalars(stmt.order_by(func.lower(Word.en), Word.id).offset(offset).limit(limit)))
    return items, total


def progress_for(db: Session, user_id: int, word_ids: list[int]) -> dict[int, dict[str, dict]]:
    """{word_id: {direction: {"box", "next_review_at", "learned"}}}."""
    out: dict[int, dict[str, dict]] = {}
    if not word_ids:
        return out
    rows = db.scalars(select(UserWordProgress).where(UserWordProgress.user_id == user_id,
                                                     UserWordProgress.word_id.in_(word_ids)))
    for p in rows:
        out.setdefault(p.word_id, {})[p.direction] = {
            "box": p.box, "next_review_at": p.next_review_at.isoformat(), "learned": p.learned}
    return out


def admin_search(db: Session, q: str | None, deck_id: int | None, status: str | None,
                 offset: int, limit: int) -> tuple[list[tuple[Word, int]], int]:
    """Слова общих отделов с числом изучающих; сортировка по updated_at убыванию."""
    learners = (select(func.count(func.distinct(UserWordProgress.user_id)))
                .where(UserWordProgress.word_id == Word.id).correlate(Word).scalar_subquery())
    stmt = select(Word, learners).join(Deck, Deck.id == Word.deck_id).where(Deck.owner_id.is_(None))
    if deck_id is not None:
        stmt = stmt.where(Word.deck_id == deck_id)
    if status is not None:
        stmt = stmt.where(Word.status == status)
    stmt = _search(stmt, q)
    total = db.scalar(select(func.count()).select_from(stmt.with_only_columns(Word.id).subquery())) or 0
    rows = db.execute(stmt.order_by(Word.updated_at.desc(), Word.id.desc()).offset(offset).limit(limit)).all()
    return [(w, n) for w, n in rows], total


def learners_count(db: Session, word_id: int) -> int:
    return db.scalar(select(func.count(func.distinct(UserWordProgress.user_id)))
                     .where(UserWordProgress.word_id == word_id)) or 0


def user_names(db: Session, ids: set[int]) -> dict[int, str]:
    """Имена авторов изменений для карточки слова в админке."""
    ids = {i for i in ids if i is not None}
    if not ids:
        return {}
    return dict(db.execute(select(User.id, User.name).where(User.id.in_(ids))).all())
