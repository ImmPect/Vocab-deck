"""Перенос гостевого прогресса (UC-03): схема журнала и функция импорта.

Контракт между модулями auth и learning. auth вызывает import_guest_progress
при регистрации и входе; реализация проверяет квитанции и «проигрывает» события
через те же правила, что и обычные ответы.
"""
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.users.models import User


class GuestEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_event_id: uuid.UUID
    word_id: int = Field(gt=0)
    direction: Literal["en_ru", "ru_en"]
    mode: Literal["deadline", "dictation", "review", "self_check"]
    is_correct: bool
    answered_at: datetime
    combo: int = Field(ge=0, le=100)
    round_id: uuid.UUID | None = None
    question_id: int | None = Field(default=None, ge=1, le=20)
    receipt: str = Field(min_length=1, max_length=128)


class GuestProgress(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format_version: Literal[1]
    events: list[GuestEvent] = Field(max_length=5000)


def import_guest_progress(db: Session, user: User, progress: GuestProgress) -> dict:
    """Проверяет и применяет журнал гостя к пользователю в текущей транзакции.

    Возвращает {"accepted", "rejected", "rejected_events": [{"client_event_id", "reason"}],
    "xp_restored", "words_transferred"}.
    """
    from app.learning.service import import_guest_events  # локальный импорт: service тяжелее схем

    return import_guest_events(db, user, progress.events)
