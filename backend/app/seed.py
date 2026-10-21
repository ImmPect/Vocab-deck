"""Начальные данные: отделы общей колоды, слова, достижения, администратор.

Запуск:  python -m app.seed
Повторный запуск безопасен: существующие записи не дублируются.
"""
import os

from sqlalchemy import func, select
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.core.db import SessionLocal, utcnow
from app.core.security import hash_password
from app.decks.models import Deck
from app.gamification.models import Achievement
from app.users.models import User
from app.seed_data import DECKS, WORDS
from app.words.models import Word

ACHIEVEMENTS = [
    ("first_round", "Первый рабочий день", {"rounds_finished": 1}),
    ("streak_7", "Неделя без прогулов", {"streak_days": 7}),
    ("words_10", "Десять слов в портфеле", {"learned_words": 10}),
    ("words_100", "Сотня слов", {"learned_words": 100}),
    ("director", "Директор", {"xp": 5000}),
]


def _resolve_rule(rule: dict | None, ids: dict[str, int]) -> dict | None:
    """{"learned_in_deck": {"deck": "Офис", ...}} → {"learned_in_deck": {"deck_id": 1, ...}}."""
    if not rule or "learned_in_deck" not in rule:
        return rule
    ref = rule["learned_in_deck"]
    return {"learned_in_deck": {"deck_id": ids[ref["deck"]], "count": ref["count"]}}


def seed(db: Session) -> dict:
    created = {"decks": 0, "words": 0, "achievements": 0, "admin": 0}
    admin_email = os.getenv("ADMIN_EMAIL", "admin@vocabdeck.local")
    admin = db.scalar(select(User).where(User.email == admin_email))
    if admin is None:
        password = os.getenv("ADMIN_PASSWORD")
        if not password:
            raise SystemExit("Задайте ADMIN_PASSWORD (см. .env.example)")
        admin = User(email=admin_email, name="Администратор", role="admin",
                     password_hash=hash_password(password), consent_at=utcnow())
        db.add(admin)
        db.flush()
        created["admin"] = 1

    ids: dict[str, int] = {}
    for title, rule, order in DECKS:
        deck = db.scalar(select(Deck).where(Deck.title == title, Deck.owner_id.is_(None)))
        if deck is None:
            deck = Deck(title=title, unlock_rule=_resolve_rule(rule, ids), sort_order=order)
            db.add(deck)
            db.flush()
            created["decks"] += 1
        ids[title] = deck.id
        for en, ipa, ru, example in WORDS[title]:
            exists = db.scalar(select(Word.id).where(Word.deck_id == deck.id, func.lower(Word.en) == en.lower()))
            if exists is None:
                db.add(Word(deck_id=deck.id, en=en, ipa=ipa, ru=ru, example=example, status="published",
                            created_by=admin.id, updated_by=admin.id))
                created["words"] += 1

    for code, title, condition in ACHIEVEMENTS:
        if db.scalar(select(Achievement.id).where(Achievement.code == code)) is None:
            db.add(Achievement(code=code, title=title, condition=condition))
            created["achievements"] += 1
    db.commit()
    return created


if __name__ == "__main__":
    from dotenv import load_dotenv  # устанавливается вместе с pydantic-settings

    from app.core.config import BASE_DIR

    load_dotenv(BASE_DIR / ".env")
    with SessionLocal() as session:
        print("Добавлено:", seed(session))
