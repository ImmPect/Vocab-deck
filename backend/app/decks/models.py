"""Модель модуля decks: отделы (общие колоды) и личные списки (таблица decks)."""
from datetime import datetime

from sqlalchemy import ForeignKey, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, BigId, JsonB, UTCDateTime, utcnow


class Deck(Base):
    __tablename__ = "decks"

    id: Mapped[int] = mapped_column(BigId, primary_key=True)
    # NULL — общий отдел, иначе — личный список пользователя
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    # Условие открытия: null, {"min_xp": 800} или {"learned_in_deck": {"deck_id": 1, "count": 20}}
    unlock_rule: Mapped[dict | None] = mapped_column(JsonB)
    sort_order: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)

    words: Mapped[list["Word"]] = relationship(back_populates="deck", cascade="all, delete-orphan",  # noqa: F821
                                               passive_deletes=True)

    @property
    def is_personal(self) -> bool:
        return self.owner_id is not None

    def __repr__(self) -> str:
        return f"<Deck {self.id} {self.title!r}>"
