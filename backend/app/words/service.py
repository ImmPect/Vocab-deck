"""Бизнес-логика модуля words: слова колод, личных списков и админки.

Сервис не знает об HTTP: при нарушениях бросает исключения из app.core.errors.
"""
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.db import utcnow
from app.core.errors import Conflict, NotFound, ValidationFailed
from app.core.responses import Page
from app.decks import repository as decks_repo
from app.decks import service as decks_service
from app.users.models import User
from app.words import repository as repo
from app.words.models import WORD_STATUSES, Word

# Допустимые переходы статуса (раздел 3.8.3)
STATUS_TRANSITIONS = {("draft", "published"), ("published", "archived"),
                      ("archived", "published"), ("draft", "archived")}


def iso(dt: datetime | None) -> str | None:
    """ISO 8601 в UTC с суффиксом Z."""
    if dt is None:
        return None
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


def field_error(field: str, message: str) -> ValidationFailed:
    return ValidationFailed(details=[{"field": field, "message": message}])


def clean_q(q: str | None) -> str | None:
    """Поиск — подстрока от 2 символов (раздел 3.1.7)."""
    if q is None:
        return None
    q = q.strip()
    if len(q) < 2:
        raise field_error("q", "Введите для поиска не менее 2 символов")
    return q


def word_out(w: Word) -> dict:
    return {"id": w.id, "deck_id": w.deck_id, "en": w.en, "ipa": w.ipa, "ru": w.ru,
            "example": w.example, "status": w.status}


def duplicate_error(existing_id: int, en: str, where: str) -> Conflict:
    return Conflict(f"Слово «{en}» уже есть {where}", code="word_duplicate",
                    details=[{"field": "en", "message": "Слово уже есть в колоде",
                              "existing_word_id": existing_id}])


# ---------- колоды и личные списки ----------

def list_deck_words(db: Session, user: User | None, deck_id: int, q: str | None, page: Page):
    """Опубликованные слова колоды; пользователю — с прогрессом по направлениям."""
    q = clean_q(q)
    decks_service.get_visible_deck(db, user, deck_id)
    words, total = repo.list_published(db, deck_id, q, page.offset, page.limit)
    items = [word_out(w) for w in words]
    if user is not None:
        progress = repo.progress_for(db, user.id, [w.id for w in words])
        for item in items:
            p = progress.get(item["id"], {})
            item["progress"] = {"en_ru": p.get("en_ru"), "ru_en": p.get("ru_en")}
    return items, page.meta(total)


def create_personal_word(db: Session, user: User, deck_id: int, data: dict) -> dict:
    deck = decks_service.get_owned_list(db, user, deck_id)
    decks_service.ensure_capacity(db, user, deck)
    existing = repo.find_duplicate(db, deck.id, data["en"])
    if existing is not None:
        raise duplicate_error(existing, data["en"], "в списке")
    word = repo.add(db, Word(deck_id=deck.id, status="published", created_by=user.id, updated_by=user.id,
                             **data))
    return word_out(word)


def _owned_word(db: Session, user: User, word_id: int) -> Word:
    """Слово своего личного списка: общий отдел — 403, чужое или нет — 404."""
    word = repo.get(db, word_id)
    if word is None:
        raise NotFound("Слово не найдено")
    decks_service.get_owned_list(db, user, word.deck_id, word_level=True)
    return word


def update_personal_word(db: Session, user: User, word_id: int, data: dict) -> dict:
    word = _owned_word(db, user, word_id)
    if "en" in data:
        existing = repo.find_duplicate(db, word.deck_id, data["en"], exclude_id=word.id)
        if existing is not None:
            raise duplicate_error(existing, data["en"], "в списке")
    for key, value in data.items():
        setattr(word, key, value)
    word.updated_by, word.updated_at = user.id, utcnow()
    db.flush()
    return word_out(word)


def delete_personal_word(db: Session, user: User, word_id: int) -> None:
    repo.delete(db, _owned_word(db, user, word_id))


# ---------- админка: общая колода ----------

def admin_word_out(db: Session, w: Word, learners: int | None = None) -> dict:
    names = repo.user_names(db, {w.created_by, w.updated_by})

    def person(uid):
        return {"id": uid, "name": names.get(uid)} if uid is not None else None

    return {
        "id": w.id, "deck": {"id": w.deck.id, "title": w.deck.title},
        "en": w.en, "ipa": w.ipa, "ru": w.ru, "example": w.example, "status": w.status,
        "created_by": person(w.created_by), "updated_by": person(w.updated_by),
        "created_at": iso(w.created_at), "updated_at": iso(w.updated_at),
        "learners_count": repo.learners_count(db, w.id) if learners is None else learners,
    }


def admin_list(db: Session, q: str | None, deck_id: int | None, status: str | None, page: Page):
    q = clean_q(q)
    if status is not None and status not in WORD_STATUSES:
        raise field_error("status", "Статус должен быть draft, published или archived")
    rows, total = repo.admin_search(db, q, deck_id, status, page.offset, page.limit)
    return [admin_word_out(db, w, n) for w, n in rows], page.meta(total)


def _shared_deck(db: Session, deck_id: int):
    deck = decks_repo.get(db, deck_id)
    if deck is None:
        raise NotFound("Отдел не найден")
    if deck.is_personal:
        raise field_error("deck_id", "Слово можно добавить только в отдел общей колоды")
    return deck


def admin_create(db: Session, admin: User, data: dict) -> dict:
    deck = _shared_deck(db, data["deck_id"])
    existing = repo.find_duplicate(db, deck.id, data["en"])
    if existing is not None:
        raise duplicate_error(existing, data["en"], f"в отделе «{deck.title}»")
    word = repo.add(db, Word(created_by=admin.id, updated_by=admin.id, **data))
    return admin_word_out(db, word, 0)


def admin_update(db: Session, admin: User, word_id: int, data: dict) -> dict:
    word = repo.get(db, word_id)
    if word is None or word.deck.is_personal:
        raise NotFound("Слово не найдено")
    # null для deck_id и status означает «не менять»
    data = {k: v for k, v in data.items() if not (k in ("deck_id", "status") and v is None)}
    deck = _shared_deck(db, data["deck_id"]) if "deck_id" in data else word.deck
    if "en" in data or deck.id != word.deck_id:
        en = data.get("en", word.en)
        existing = repo.find_duplicate(db, deck.id, en, exclude_id=word.id)
        if existing is not None:
            raise duplicate_error(existing, en, f"в отделе «{deck.title}»")
    new_status = data.get("status")
    if new_status is not None and new_status != word.status \
            and (word.status, new_status) not in STATUS_TRANSITIONS:
        raise Conflict(f"Нельзя перевести слово из статуса {word.status} в {new_status}",
                       code="invalid_status_transition")
    for key, value in data.items():
        setattr(word, key, value)
    word.updated_by, word.updated_at = admin.id, utcnow()
    db.flush()
    db.refresh(word)
    return admin_word_out(db, word)
