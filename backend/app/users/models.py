"""Модели модуля users: пользователи и их сессии (таблицы users, sessions)."""
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, SmallInteger, String, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, BigId, UTCDateTime, utcnow


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'admin')", name="ck_users_role"),
        CheckConstraint("streak_freezes BETWEEN 0 AND 2", name="ck_users_streak_freezes"),
    )

    id: Mapped[int] = mapped_column(BigId, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(10), nullable=False, default="user", server_default="user")
    # Кэш, источник истины — журнал answer_events (п. 1.3 ПР3)
    xp: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    streak_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    streak_freezes: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0, server_default="0")
    last_active_date: Mapped[date | None] = mapped_column(Date)
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="Europe/Moscow",
                                          server_default="Europe/Moscow")
    failed_logins: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0, server_default="0")
    locked_until: Mapped[datetime | None] = mapped_column(UTCDateTime)
    consent_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)

    sessions: Mapped[list["UserSession"]] = relationship(back_populates="user", cascade="all, delete-orphan",
                                                         passive_deletes=True)

    def __repr__(self) -> str:
        return f"<User {self.id} {self.email} role={self.role}>"


class UserSession(Base):
    """Сессия входа. id — случайный токен из cookie session_id."""

    __tablename__ = "sessions"
    __table_args__ = (Index("ix_sessions_user_id", "user_id"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)

    user: Mapped[User] = relationship(back_populates="sessions")
