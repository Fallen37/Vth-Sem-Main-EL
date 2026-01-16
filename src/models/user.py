"""User model - SQLAlchemy and Pydantic schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import String, Integer, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.sqlite import JSON

from src.models.database import Base
from src.models.enums import UserRole, Syllabus


# SQLAlchemy Model
class UserORM(Base):
    """SQLAlchemy User model."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    role: Mapped[str] = mapped_column(SQLEnum(UserRole), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    grade: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    syllabus: Mapped[Optional[str]] = mapped_column(SQLEnum(Syllabus), nullable=True)
    linked_guardian_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    linked_student_ids: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    learning_profile = relationship("LearningProfileORM", back_populates="user", uselist=False)
    sessions = relationship("SessionORM", back_populates="user")
    progress_records = relationship("ProgressORM", back_populates="user")
    achievements = relationship("AchievementORM", back_populates="user")


# Pydantic Schemas
class UserBase(BaseModel):
    """Base user schema."""

    email: EmailStr
    name: str
    role: UserRole


class UserCreate(UserBase):
    """Schema for creating a user."""

    grade: Optional[int] = Field(None, ge=5, le=10)
    syllabus: Optional[Syllabus] = None
    linked_guardian_id: Optional[UUID] = None


class UserUpdate(BaseModel):
    """Schema for updating a user."""

    name: Optional[str] = None
    grade: Optional[int] = Field(None, ge=5, le=10)
    syllabus: Optional[Syllabus] = None
    linked_guardian_id: Optional[UUID] = None


class User(UserBase):
    """Full user schema."""

    id: UUID
    grade: Optional[int] = None
    syllabus: Optional[Syllabus] = None
    linked_guardian_id: Optional[UUID] = None
    linked_student_ids: list[UUID] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
