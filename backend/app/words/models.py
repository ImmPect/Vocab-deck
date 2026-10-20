"""Модель модуля words: карточки слов (таблица words)."""
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, BigId, UTCDateTime, utcnow

WORD_STATUSES = ("draft", "published", "archived")


class Word(Base):
    __tablename__ = "words"
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'published', 'archived')", name="ck_words_status"),
        # Дубликат слова в одной колоде запрещён без учёта регистра (US-12)
        Index("ux_words_deck_en", "deck_id", text("lower(en)"), unique=True),
    )

    id: Mapped[int] = mapped_column(BigId, primary_key=True)
    deck_id: Mapped[int] = mapped_column(ForeignKey("decks.id", ondelete="CASCADE"), nullable=False)
    # Допустимые символы (латиница, пробел, дефис, апостроф) проверяет Pydantic-схема
    en: Mapped[str] = mapped_column(String(100), nullable=False)
    ipa: Mapped[str | None] = mapped_column(String(100))
    ru: Mapped[str] = mapped_column(String(200), nullable=False)
    example: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="published")
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow, onupdate=utcnow)

    deck: Mapped["Deck"] = relationship(back_populates="words")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Word {self.id} {self.en!r} [{self.status}]>"
