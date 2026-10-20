"""Схемы запросов модуля decks (разделы 3.5.3, 3.5.4 ПР3)."""
from pydantic import BaseModel, ConfigDict, field_validator

TITLE_MAX = 100


def clean_title(value: str | None) -> str:
    v = (value or "").strip()
    if not v:
        raise ValueError("Введите название")
    if len(v) > TITLE_MAX:
        raise ValueError(f"Название должно быть не длиннее {TITLE_MAX} символов")
    return v


class DeckIn(BaseModel):
    """POST /decks и PATCH /decks/{deck_id}: только название личного списка."""

    model_config = ConfigDict(extra="forbid")

    title: str

    @field_validator("title")
    @classmethod
    def _title(cls, v):
        return clean_title(v)
