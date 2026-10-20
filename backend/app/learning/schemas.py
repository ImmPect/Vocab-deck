"""Pydantic-схемы запросов модуля learning (раздел 3.7 ПР3)."""
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Direction = Literal["en_ru", "ru_en"]


class RoundCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    deck_id: int = Field(gt=0)
    mode: Literal["deadline", "dictation"]
    direction: Direction = "en_ru"


class AnswerCreate(BaseModel):
    """Ответ на вопрос раунда. choice_index — для deadline, text — для dictation."""

    model_config = ConfigDict(extra="forbid")

    question_id: int = Field(ge=1, le=5)
    choice_index: int | None = Field(default=None, ge=0, le=3)
    text: str | None = Field(default=None, max_length=100)
    client_event_id: uuid.UUID
    answered_at: datetime
    response_ms: int | None = Field(default=None, ge=0, le=60000)
    # Только для гостя: текущий ящик слова из localStorage; пользователю игнорируется
    current_box: int | None = Field(default=None, ge=1, le=5)


class BatchAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_event_id: uuid.UUID
    mode: Literal["self_check", "review", "deadline", "dictation"]
    word_id: int = Field(gt=0)
    direction: Direction
    is_correct: bool | None = None
    round_id: uuid.UUID | None = None
    question_id: int | None = Field(default=None, ge=1, le=5)
    choice_index: int | None = Field(default=None, ge=0, le=3)
    text: str | None = Field(default=None, max_length=100)
    answered_at: datetime
    response_ms: int | None = Field(default=None, ge=0, le=600000)
    current_box: int | None = Field(default=None, ge=1, le=5)

    @model_validator(mode="after")
    def _required_by_mode(self):
        if self.mode in ("self_check", "review") and self.is_correct is None:
            raise ValueError("Для self_check и review укажите is_correct")
        if self.mode in ("deadline", "dictation") and (self.round_id is None or self.question_id is None):
            raise ValueError("Для ответа раунда укажите round_id и question_id")
        return self


class BatchCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answers: list[BatchAnswer] = Field(min_length=1, max_length=200)
