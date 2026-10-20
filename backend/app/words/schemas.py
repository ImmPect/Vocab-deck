"""Схемы и правила проверки полей слова (разделы 3.6.2, 3.8.2 ПР3).

Функции clean_* используются и Pydantic-схемами, и импортом CSV,
поэтому слово из формы и строка файла проверяются одинаково.
"""
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

EN_RE = re.compile(r"^[A-Za-z' -]+$")
EN_MAX, RU_MAX, IPA_MAX, EXAMPLE_MAX = 100, 200, 100, 500

MSG_EN_CHARS = "Допустимы латинские буквы, пробел, дефис и апостроф"


def clean_en(value: str | None) -> str:
    v = (value or "").strip()
    if not v:
        raise ValueError("Заполните слово на английском")
    if len(v) > EN_MAX:
        raise ValueError(f"Слово должно быть не длиннее {EN_MAX} символов")
    if not EN_RE.match(v) or not re.search(r"[A-Za-z]", v):
        raise ValueError(MSG_EN_CHARS)
    return v


def clean_ru(value: str | None) -> str:
    v = (value or "").strip()
    if not v:
        raise ValueError("Заполните перевод")
    if len(v) > RU_MAX:
        raise ValueError(f"Перевод должен быть не длиннее {RU_MAX} символов")
    return v


def _optional(value: str | None, limit: int, what: str) -> str | None:
    if value is None:
        return None
    v = value.strip()
    if len(v) > limit:
        raise ValueError(f"{what} должна быть не длиннее {limit} символов")
    return v or None


def clean_ipa(value: str | None) -> str | None:
    return _optional(value, IPA_MAX, "Транскрипция")


def clean_example(value: str | None) -> str | None:
    if value is not None and len(value.strip()) > EXAMPLE_MAX:
        raise ValueError(f"Пример должен быть не длиннее {EXAMPLE_MAX} символов")
    return (value or "").strip() or None


class _WordFields(BaseModel):
    """Общие проверки полей en, ru, ipa, example."""

    model_config = ConfigDict(extra="forbid")

    @field_validator("en", check_fields=False)
    @classmethod
    def _en(cls, v):
        return clean_en(v)

    @field_validator("ru", check_fields=False)
    @classmethod
    def _ru(cls, v):
        return clean_ru(v)

    @field_validator("ipa", check_fields=False)
    @classmethod
    def _ipa(cls, v):
        return clean_ipa(v)

    @field_validator("example", check_fields=False)
    @classmethod
    def _example(cls, v):
        return clean_example(v)


class WordCreate(_WordFields):
    """POST /decks/{deck_id}/words."""

    en: str
    ru: str
    ipa: str | None = None
    example: str | None = None


class WordUpdate(_WordFields):
    """PATCH /words/{word_id}: любое подмножество полей."""

    en: str | None = None
    ru: str | None = None
    ipa: str | None = None
    example: str | None = None


class AdminWordCreate(WordCreate):
    """POST /admin/words."""

    deck_id: int
    status: Literal["draft", "published"] = "draft"


class AdminWordUpdate(WordUpdate):
    """PATCH /admin/words/{word_id}."""

    deck_id: int | None = None
    status: Literal["draft", "published", "archived"] | None = None
