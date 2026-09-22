import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base


class InterviewRoom(Base):
    __tablename__ = "interview_rooms"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    difficulty: Mapped[str] = mapped_column(String(20), nullable=False, default="Medium")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class InterviewProblem(Base):
    """A seeded interview question, keyed by room and round slot (1 or 2)."""
    __tablename__ = "interview_problems"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("interview_rooms.id", ondelete="CASCADE"), nullable=False)
    slot: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())



class InterviewSession(Base):

    participants: Mapped[list[InterviewParticipant]] = relationship("InterviewParticipant", back_populates="session", cascade="all, delete-orphan")
    rounds: Mapped[list[InterviewRound]] = relationship("InterviewRound", back_populates="session", cascade="all, delete-orphan")

    __tablename__ = "interview_sessions"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("interview_rooms.id"), nullable=False)
    mode: Mapped[str] = mapped_column(String(50), nullable=False, default="STANDARD")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="CREATED")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    abandoned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class InterviewParticipant(Base):

    session: Mapped[InterviewSession] = relationship("InterviewSession", back_populates="participants")
    round_roles: Mapped[list[RoundParticipant]] = relationship("RoundParticipant", back_populates="participant", cascade="all, delete-orphan")

    __tablename__ = "interview_participants"
    
    __table_args__ = (
        UniqueConstraint("session_id", "user_id", name="uq_session_user"),
        UniqueConstraint("session_id", "seat", name="uq_session_seat"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    seat: Mapped[int] = mapped_column(Integer, nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class InterviewRound(Base):
    __tablename__ = "interview_rounds"

    __table_args__ = (
        UniqueConstraint("session_id", "round_number", name="uq_session_round"),
        CheckConstraint("round_number BETWEEN 1 AND 2", name="chk_round_number"),
    )
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="PENDING")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # An interviewer's explicit choice for this round, made from the
    # suggested bank (problem_id) or written free-hand (custom_problem_text).
    # At most one is set at a time. Neither being set means "not chosen yet";
    # the round falls back to the existing deterministic auto-pick once it
    # actually starts (picking a question is a suggestion, not mandatory).
    problem_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("interview_problems.id", ondelete="SET NULL"), nullable=True)
    custom_problem_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    session: Mapped[InterviewSession] = relationship("InterviewSession", back_populates="rounds")
    round_participants: Mapped[list[RoundParticipant]] = relationship("RoundParticipant", back_populates="round", cascade="all, delete-orphan")
    feedbacks: Mapped[list[Feedback]] = relationship("Feedback", back_populates="round", cascade="all, delete-orphan")

class RoundParticipant(Base):
    __tablename__ = "round_participants"

    __table_args__ = (
        UniqueConstraint("round_id", "participant_id", name="uq_round_participant"),
    )
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    round_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("interview_rounds.id", ondelete="CASCADE"), nullable=False)
    participant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("interview_participants.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)

    round: Mapped[InterviewRound] = relationship("InterviewRound", back_populates="round_participants")
    participant: Mapped[InterviewParticipant] = relationship("InterviewParticipant", back_populates="round_roles")

class Feedback(Base):
    __tablename__ = "feedback"

    __table_args__ = (
        UniqueConstraint("round_id", "giver_participant_id", "receiver_participant_id", name="uq_feedback_duplicate"),
        CheckConstraint("giver_participant_id != receiver_participant_id", name="chk_feedback_direction"),
    )
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    round_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("interview_rounds.id", ondelete="CASCADE"), nullable=False)
    giver_participant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("interview_participants.id", ondelete="CASCADE"), nullable=False)
    receiver_participant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("interview_participants.id", ondelete="CASCADE"), nullable=False)
    evaluated_role: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="PENDING")
    
    from sqlalchemy.dialects.postgresql import JSONB
    scores: Mapped[dict | None] = mapped_column(JSONB)
    comments: Mapped[str | None] = mapped_column(Text)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    round: Mapped[InterviewRound] = relationship("InterviewRound", back_populates="feedbacks")
    giver: Mapped[InterviewParticipant] = relationship("InterviewParticipant", foreign_keys=[giver_participant_id])
    receiver: Mapped[InterviewParticipant] = relationship("InterviewParticipant", foreign_keys=[receiver_participant_id])
