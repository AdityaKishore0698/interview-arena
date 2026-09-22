import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base


class User(Base):
    __tablename__ = "users"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    auth_provider: Mapped[str] = mapped_column(String(50), default="local")
    is_verified: Mapped[bool] = mapped_column(default=False)
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE")
    # Bumped on every login (password, Google) and on logout. Each issued JWT
    # embeds the value current at issue time ("sv" claim); a request is only
    # honored if that still matches — so signing in on a second device (or
    # explicitly logging out) invalidates whatever token was issued before,
    # enforcing one active session per account. A token with no "sv" claim
    # (issued before this existed) is treated as version 0, matching this
    # column's default — existing sessions keep working until their next
    # login, rather than every logged-in user being signed out at once.
    session_version: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    profile: Mapped[Profile] = relationship("Profile", back_populates="user", uselist=False, cascade="all, delete-orphan")

class Profile(Base):
    __tablename__ = "profiles"
    
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    # A small (client-resized) image as a data: URI, or an https:// URL. Stored
    # as plain text rather than in object storage — this is a demo app and an
    # avatar capped at a few hundred KB is a reasonable fit for a text column.
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    user: Mapped[User] = relationship("User", back_populates="profile")


class UserStreak(Base):
    """Daily login and interview streaks. One row per user, created lazily on
    first check-in / first completed interview rather than at signup."""
    __tablename__ = "user_streaks"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    login_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    longest_login_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    login_streak_last_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    interview_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    longest_interview_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    interview_streak_last_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
