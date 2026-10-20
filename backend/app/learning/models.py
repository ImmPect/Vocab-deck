"""Модели модуля learning: прогресс по словам, журнал ответов, раунды мини-игр."""
import uuid
from datetime import date, datetime

from sqlalchemy import (Boolean, CheckConstraint, Date, ForeignKey, Index, Integer, SmallInteger,
                        String, Uuid)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, BigId, JsonB, UTCDateTime, utcnow

DIRECTIONS = ("en_ru", "ru_en")
ROUND_MODES = ("deadline", "dictation")
ANSWER_MODES = ("deadline", "dictation", "review", "self_check")


class UserWordProgress(Base):
    """Текущее состояние слова у пользователя: ящик Лейтнера и дата повтора."""

    __tablename__ = "user_word_progress"
    __table_args__ = (
        CheckConstraint("direction IN ('en_ru', 'ru_en')", name="ck_uwp_direction"),
        CheckConstraint("box BETWEEN 1 AND 5", name="ck_uwp_box"),
        Index("ix_uwp_user_next_review", "user_id", "next_review_at"),  # выборка входящих (NFR-M-02)
    )

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    word_id: Mapped[int] = mapped_column(ForeignKey("words.id", ondelete="CASCADE"), primary_key=True)
    direction: Mapped[str] = mapped_column(String(5), primary_key=True)
    box: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    next_review_at: Mapped[date] = mapped_column(Date, nullable=False)
    learned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow, onupdate=utcnow)


class AnswerEvent(Base):
    """Журнал ответов: каждая строка — один ответ, строки не изменяются."""

    __tablename__ = "answer_events"
    __table_args__ = (
        CheckConstraint("mode IN ('deadline', 'dictation', 'review', 'self_check')", name="ck_ae_mode"),
        CheckConstraint("direction IN ('en_ru', 'ru_en')", name="ck_ae_direction"),
        Index("ix_ae_user_created", "user_id", "created_at"),  # статистика за период
    )

    id: Mapped[int] = mapped_column(BigId, primary_key=True)
    # Ключ идемпотентности: повторная отправка не начисляет опыт повторно (NFR-R-02)
    client_event_id: Mapped[uuid.UUID] = mapped_column(Uuid, unique=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    word_id: Mapped[int] = mapped_column(ForeignKey("words.id", ondelete="CASCADE"), nullable=False)
    round_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("rounds.id", ondelete="SET NULL"))
    direction: Mapped[str] = mapped_column(String(5), nullable=False)
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    response_ms: Mapped[int | None] = mapped_column(Integer)
    xp_awarded: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    answered_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)


class Round(Base):
    """Начатый раунд мини-игры. Хранится в БД, чтобы API оставался stateless (NFR-M-01).

    questions — список объектов {"question_id", "word_id", "options", "correct_index", "answer"};
    правильные ответы клиенту до ответа не отдаются.
    """

    __tablename__ = "rounds"
    __table_args__ = (
        CheckConstraint("mode IN ('deadline', 'dictation')", name="ck_rounds_mode"),
        CheckConstraint("direction IN ('en_ru', 'ru_en')", name="ck_rounds_direction"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))  # NULL — гость
    deck_id: Mapped[int] = mapped_column(ForeignKey("decks.id", ondelete="CASCADE"), nullable=False)
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    direction: Mapped[str] = mapped_column(String(5), nullable=False)
    questions: Mapped[list] = mapped_column(JsonB, nullable=False)
    current_combo: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    started_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
