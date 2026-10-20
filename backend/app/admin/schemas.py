"""Схемы запросов модуля admin (раздел 3.8 ПР3).

Схемы слов общей колоды — в app.words.schemas (AdminWordCreate, AdminWordUpdate).
"""
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

from app.decks.schemas import clean_title

SORT_ORDER_MAX = 32767  # SMALLINT


def _non_negative_int(value: Any, field: str, minimum: int = 0) -> int:
    # bool — подкласс int в Python, его отклоняем явно
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise ValueError(f"{field}: нужно целое число не меньше {minimum}")
    return value


def clean_unlock_rule(rule: Any) -> dict | None:
    """null, {"min_xp": n} или {"learned_in_deck": {"deck_id": id, "count": n}}."""
    if rule is None:
        return None
    if not isinstance(rule, dict) or len(rule) != 1:
        raise ValueError("Условие открытия: null, {\"min_xp\": n} или {\"learned_in_deck\": {...}}")
    (key, value), = rule.items()
    if key == "min_xp":
        return {"min_xp": _non_negative_int(value, "min_xp")}
    if key == "learned_in_deck":
        if not isinstance(value, dict) or set(value) != {"deck_id", "count"}:
            raise ValueError("learned_in_deck должно содержать ровно поля deck_id и count")
        return {"learned_in_deck": {"deck_id": _non_negative_int(value["deck_id"], "deck_id", 1),
                                    "count": _non_negative_int(value["count"], "count", 1)}}
    raise ValueError(f"Неизвестное условие открытия: {key}")


class AdminDeckCreate(BaseModel):
    """POST /admin/decks."""

    model_config = ConfigDict(extra="forbid")

    title: str
    unlock_rule: Any = None
    sort_order: int | None = None

    @field_validator("title")
    @classmethod
    def _title(cls, v):
        return clean_title(v)

    @field_validator("unlock_rule")
    @classmethod
    def _rule(cls, v):
        return clean_unlock_rule(v)

    @field_validator("sort_order")
    @classmethod
    def _order(cls, v):
        if v is not None and not 0 <= v <= SORT_ORDER_MAX:
            raise ValueError(f"Порядок должен быть от 0 до {SORT_ORDER_MAX}")
        return v


class AdminDeckUpdate(AdminDeckCreate):
    """PATCH /admin/decks/{deck_id}: передаются только изменяемые поля."""

    title: str | None = None
