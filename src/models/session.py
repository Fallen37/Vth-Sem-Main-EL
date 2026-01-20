"""Session and Message models - SQLAlchemy and Pydantic schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.sqlite import JSON

from src.models.database import Base
from src.models.enums import InputType, MessageRole, ComprehensionLevel


# SQLAlchemy Models
class SessionORM(Base):
    """SQLAlchemy Session model."""

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    chapter: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    current_topic_index: Mapped[int] = mapped_column(Integer, default=0)
    topics_list: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    topics_covered: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    comprehension_scores: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    guardian_input_count: Mapped[int] = mapped_column(Integer, default=0)
    student_input_count: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    user = relationship("UserORM", back_populates="sessions")
    messages = relationship("MessageORM", back_populates="session", cascade="all, delete-orphan")


class MessageORM(Base):
    """SQLAlchemy Message model."""

    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sessions.id"), nullable=False
    )
    role: Mapped[str] = mapped_column(SQLEnum(MessageRole), nullable=False)
    input_type: Mapped[str] = mapped_column(SQLEnum(InputType), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    audio_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    visual_aid_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    comprehension_feedback: Mapped[Optional[str]] = mapped_column(
        SQLEnum(ComprehensionLevel), nullable=True
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    session = relationship("SessionORM", back_populates="messages")


# Pydantic Schemas
class MessageBase(BaseModel):
    """Base message schema."""

    role: MessageRole
    input_type: InputType
    content: str


class MessageCreate(MessageBase):
    """Schema for creating a message."""

    session_id: UUID
    audio_url: Optional[str] = None
    visual_aid_url: Optional[str] = None
    comprehension_feedback: Optional[ComprehensionLevel] = None


class Message(MessageBase):
    """Full message schema."""

    id: UUID
    session_id: UUID
    audio_url: Optional[str] = None
    visual_aid_url: Optional[str] = None
    comprehension_feedback: Optional[ComprehensionLevel] = None
    timestamp: datetime

    class Config:
        from_attributes = True


class SessionBase(BaseModel):
    """Base session schema."""

    user_id: UUID


class SessionCreate(SessionBase):
    """Schema for creating a session."""

    pass


class SessionUpdate(BaseModel):
    """Schema for updating a session."""

    ended_at: Optional[datetime] = None
    topics_covered: Optional[list[str]] = None
    comprehension_scores: Optional[dict[str, float]] = None


class Session(SessionBase):
    """Full session schema."""

    id: UUID
    started_at: datetime
    ended_at: Optional[datetime] = None
    topics_covered: list[str] = []
    comprehension_scores: dict[str, float] = {}
    guardian_input_count: int = 0
    student_input_count: int = 0
    messages: list[Message] = []

    class Config:
        from_attributes = True
