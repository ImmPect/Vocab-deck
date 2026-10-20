"""Бизнес-логика модуля decks: отделы, личные списки, условия открытия, импорт CSV.

Прогресс и число выученных слов берутся только из app.learning.stats.
"""
from sqlalchemy.orm import Session

from app.core.errors import Conflict, Forbidden, NotFound, ValidationFailed
from app.decks import csv_import
from app.decks import repository as repo
from app.decks.models import Deck
from app.gamification.rules import LEVELS, PERSONAL_LIST_LIMIT, features_for
from app.learning.stats import deck_progress, learned_in_deck
from app.users.models import User
from app.words import repository as words_repo
from app.words.models import Word

KINDS = ("shared", "personal")


# ---------- условие открытия ----------

def _plural_words(n: int) -> str:
    if n % 10 == 1 and n % 100 != 11:
        return "слово"
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return "слова"
    return "слов"


def unlock_condition(rule: dict | None, titles: dict[int, str]) -> str | None:
    """Текст условия открытия для плитки отдела (NFR-O-04)."""
    if not rule:
        return None
    if "min_xp" in rule:
        xp = rule["min_xp"]
        level = next((lvl for lvl in LEVELS if lvl["min_xp"] == xp), None)
        if level:
            return f"Откроется на должности «{level['title']}» ({xp} опыта)"
        return f"Откроется, когда вы наберёте {xp} опыта"
    if "learned_in_deck" in rule:
        ref = rule["learned_in_deck"]
        count, title = ref["count"], titles.get(ref["deck_id"], "?")
        return f"Откроется, когда вы выучите {count} {_plural_words(count)} в отделе «{title}»"
    return None


def is_locked(db: Session, rule: dict | None, user: User | None) -> bool:
    """Закрыт ли отдел для пользователя; для гостя — при нулевом прогрессе."""
    if not rule:
        return False
    if "min_xp" in rule:
        return (user.xp if user else 0) < rule["min_xp"]
    if "learned_in_deck" in rule:
        ref = rule["learned_in_deck"]
        learned = learned_in_deck(db, user.id, ref["deck_id"]) if user else 0
        return learned < ref["count"]
    return False


def _rule_titles(db: Session, decks: list[Deck]) -> dict[int, str]:
    ids = {d.unlock_rule["learned_in_deck"]["deck_id"] for d in decks
           if d.unlock_rule and "learned_in_deck" in d.unlock_rule}
    return repo.titles(db, ids)


def decks_out(db: Session, decks: list[Deck], user: User | None) -> list[dict]:
    """Колоды в формате элемента GET /decks."""
    progress = deck_progress(db, user.id if user else None, [d.id for d in decks])
    titles = _rule_titles(db, decks)
    out = []
    for d in decks:
        p = progress[d.id]
        out.append({
            "id": d.id, "kind": "personal" if d.is_personal else "shared", "title": d.title,
            "sort_order": d.sort_order, "words_count": p["total"],
            "progress": {k: p[k] for k in ("learned", "in_progress", "new")} if user else None,
            "locked": is_locked(db, d.unlock_rule, user),
            "unlock_rule": d.unlock_rule, "unlock_condition": unlock_condition(d.unlock_rule, titles),
        })
    return out


def deck_out(db: Session, deck: Deck, user: User | None) -> dict:
    item = decks_out(db, [deck], user)[0]
    item["can_edit"] = user is not None and deck.owner_id == user.id
    return item


# ---------- проверки доступа (используются и модулем words) ----------

def get_visible_deck(db: Session, user: User | None, deck_id: int) -> Deck:
    """Общий отдел или свой личный список; чужой список не раскрывается (404)."""
    deck = repo.get(db, deck_id)
    if deck is None or (deck.is_personal and (user is None or deck.owner_id != user.id)):
        raise NotFound("Колода не найдена")
    return deck


def get_owned_list(db: Session, user: User, deck_id: int, *, word_level: bool = False) -> Deck:
    """Свой личный список: общий отдел — 403, чужой или несуществующий — 404."""
    deck = repo.get(db, deck_id)
    if deck is None or (deck.is_personal and deck.owner_id != user.id):
        raise NotFound("Слово не найдено" if word_level else "Список не найден")
    if not deck.is_personal:
        raise Forbidden("Общая колода изменяется только администратором")
    return deck


def has_unlimited_lists(user: User) -> bool:
    return features_for(user.xp)["unlimited_lists"]


def ensure_capacity(db: Session, user: User, deck: Deck) -> None:
    """Лимит размера личного списка до должности «Руководитель отдела» (табл. 4)."""
    if not has_unlimited_lists(user) and words_repo.count_in_deck(db, deck.id) >= PERSONAL_LIST_LIMIT:
        raise Forbidden(f"В личном списке может быть не больше {PERSONAL_LIST_LIMIT} слов "
                        "до должности «Руководитель отдела»", code="limit_reached")


# ---------- пользовательские операции ----------

def list_decks(db: Session, user: User | None, kind: str | None) -> list[dict]:
    if kind is not None and kind not in KINDS:
        raise ValidationFailed(details=[{"field": "kind", "message": "Допустимые значения: shared, personal"}])
    decks: list[Deck] = []
    if kind in (None, "shared"):
        decks += repo.list_shared(db)
    if kind in (None, "personal") and user is not None:
        decks += repo.list_personal(db, user.id)
    return decks_out(db, decks, user)


def get_deck(db: Session, user: User | None, deck_id: int) -> dict:
    return deck_out(db, get_visible_deck(db, user, deck_id), user)


def create_list(db: Session, user: User, title: str) -> dict:
    deck = repo.add(db, Deck(owner_id=user.id, title=title, sort_order=0))
    return deck_out(db, deck, user)


def rename_list(db: Session, user: User, deck_id: int, title: str) -> dict:
    deck = get_owned_list(db, user, deck_id)
    deck.title = title
    db.flush()
    return deck_out(db, deck, user)


def delete_list(db: Session, user: User, deck_id: int) -> None:
    """Слова и прогресс по ним удаляются каскадом в БД; опыт не списывается."""
    repo.delete(db, get_owned_list(db, user, deck_id))


def import_csv(db: Session, user: User, deck_id: int, raw: bytes) -> dict:
    """Импорт строк CSV одной транзакцией с отчётом по пропущенным строкам (US-10)."""
    deck = get_owned_list(db, user, deck_id)
    csv_import.check_size(raw)
    ensure_capacity(db, user, deck)  # список уже полон — как при добавлении одного слова
    rows = csv_import.parse(raw)

    seen = words_repo.existing_en(db, deck.id)
    room = None if has_unlimited_lists(user) else PERSONAL_LIST_LIMIT - len(seen)
    added, skipped = 0, []
    for row in rows:
        data, err = csv_import.validate(row)
        if err is None and data["en"].lower() in seen:
            err = csv_import.RowError(row.line, data["en"], "duplicate", "Слово уже есть в списке")
        if err is None and room is not None and added >= room:
            err = csv_import.RowError(row.line, data["en"], "limit_reached",
                                      f"Достигнут лимит списка: {PERSONAL_LIST_LIMIT} слов")
        if err is not None:
            skipped.append(err.as_dict())
            continue
        seen.add(data["en"].lower())
        db.add(Word(deck_id=deck.id, status="published", created_by=user.id, updated_by=user.id, **data))
        added += 1
    db.flush()
    return {"total_rows": len(rows), "added": added, "skipped": skipped}


# ---------- админка: отделы ----------

def _check_rule_ref(db: Session, rule: dict | None, deck_id: int | None = None) -> None:
    if rule and "learned_in_deck" in rule:
        ref_id = rule["learned_in_deck"]["deck_id"]
        ref = repo.get(db, ref_id)
        if ref is None or ref.is_personal:
            raise NotFound("Отдел из условия открытия не найден")
        if ref_id == deck_id:
            raise ValidationFailed(details=[{"field": "unlock_rule.learned_in_deck.deck_id",
                                             "message": "Отдел не может ссылаться сам на себя"}])


def _check_title(db: Session, title: str, exclude_id: int | None = None) -> None:
    if repo.shared_title_exists(db, title, exclude_id):
        raise Conflict(f"Отдел «{title}» уже есть", code="deck_title_taken")


def admin_create_deck(db: Session, admin: User, data: dict) -> dict:
    _check_title(db, data["title"])
    _check_rule_ref(db, data.get("unlock_rule"))
    deck = repo.add(db, Deck(owner_id=None, title=data["title"], unlock_rule=data.get("unlock_rule"),
                             sort_order=data.get("sort_order") or 0))
    return deck_out(db, deck, admin)


def admin_update_deck(db: Session, admin: User, deck_id: int, data: dict) -> dict:
    deck = repo.get(db, deck_id)
    if deck is None or deck.is_personal:
        raise NotFound("Отдел не найден")
    if data.get("title") is not None:
        _check_title(db, data["title"], exclude_id=deck.id)
        deck.title = data["title"]
    if "unlock_rule" in data:
        _check_rule_ref(db, data["unlock_rule"], deck.id)
        deck.unlock_rule = data["unlock_rule"]
    if data.get("sort_order") is not None:
        deck.sort_order = data["sort_order"]
    db.flush()
    return deck_out(db, deck, admin)
