"""Запросы к таблице decks."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.decks.models import Deck


def get(db: Session, deck_id: int) -> Deck | None:
    return db.get(Deck, deck_id)


def list_shared(db: Session) -> list[Deck]:
    return list(db.scalars(select(Deck).where(Deck.owner_id.is_(None)).order_by(Deck.sort_order, Deck.id)))


def list_personal(db: Session, owner_id: int) -> list[Deck]:
    return list(db.scalars(select(Deck).where(Deck.owner_id == owner_id).order_by(Deck.created_at, Deck.id)))


def titles(db: Session, ids: set[int]) -> dict[int, str]:
    if not ids:
        return {}
    return dict(db.execute(select(Deck.id, Deck.title).where(Deck.id.in_(ids))).all())


def shared_title_exists(db: Session, title: str, exclude_id: int | None = None) -> bool:
    """Есть ли отдел с таким названием (без учёта регистра).

    Сравнение в Python: lower() в SQLite не понижает кириллицу, а отделов немного.
    """
    stmt = select(Deck.title).where(Deck.owner_id.is_(None))
    if exclude_id is not None:
        stmt = stmt.where(Deck.id != exclude_id)
    return title.casefold() in {t.casefold() for t in db.scalars(stmt)}


def add(db: Session, deck: Deck) -> Deck:
    db.add(deck)
    db.flush()
    return deck


def delete(db: Session, deck: Deck) -> None:
    db.delete(deck)
    db.flush()
