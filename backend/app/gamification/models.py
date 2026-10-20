"""Модели модуля gamification: справочник достижений и полученные достижения."""
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, true
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, JsonB, UTCDateTime, utcnow


class Achievement(Base):
    __tablename__ = "achievements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    # Например {"streak_days": 7}, {"learned_words": 100}, {"xp": 5000}
    condition: Mapped[dict] = mapped_column(JsonB, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())


class UserAchievement(Base):
    __tablename__ = "user_achievements"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    achievement_id: Mapped[int] = mapped_column(ForeignKey("achievements.id", ondelete="CASCADE"),
                                                primary_key=True)
    earned_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)
