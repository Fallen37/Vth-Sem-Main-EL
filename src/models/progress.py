"""Progress and Achievement models - SQLAlchemy and Pydantic schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.database import Base


# SQLAlchemy Models
class ProgressORM(Base):
    """SQLAlchemy Progress model."""

    __tablename__ = "progress"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    topic_id: Mapped[str] = mapped_column(String(100), nullable=False)
    topic_name: Mapped[str] = mapped_column(String(255), nullable=False)
    grade: Mapped[int] = mapped_column(Integer, nullable=False)
    comprehension_level: Mapped[float] = mapped_column(Float, default=0.0)
    times_reviewed: Mapped[int] = mapped_column(Integer, default=0)
    last_reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    user = relationship("UserORM", back_populates="progress_records")


class AchievementORM(Base):
    """SQLAlchemy Achievement model."""

    __tablename__ = "achievements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    achievement_type: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    earned_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("UserORM", back_populates="achievements")


# Pydantic Schemas
class Topic(BaseModel):
    """Topic reference."""

    topic_id: str
    topic_name: str
    grade: int = Field(ge=5, le=10)


class ProgressBase(BaseModel):
    """Base progress schema."""

    user_id: UUID
    topic_id: str
    topic_name: str
    grade: int = Field(ge=5, le=10)


class ProgressCreate(ProgressBase):
    """Schema for creating a progress record."""

    comprehension_level: float = Field(0.0, ge=0.0, le=1.0)


class ProgressUpdate(BaseModel):
    """Schema for updating a progress record."""

    comprehension_level: Optional[float] = Field(None, ge=0.0, le=1.0)
    times_reviewed: Optional[int] = None
    last_reviewed_at: Optional[datetime] = None


class Progress(ProgressBase):
    """Full progress schema."""

    id: UUID
    comprehension_level: float = Field(ge=0.0, le=1.0)
    times_reviewed: int = 0
    last_reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AchievementBase(BaseModel):
    """Base achievement schema."""

    achievement_type: str
    title: str
    description: str


class AchievementCreate(AchievementBase):
    """Schema for creating an achievement."""

    user_id: UUID


class Achievement(AchievementBase):
    """Full achievement schema."""

    id: UUID
    user_id: UUID
    earned_at: datetime

    class Config:
        from_attributes = True


class ProgressSummary(BaseModel):
    """Progress summary for child-friendly display."""

    topics_covered: int
    total_topics: int
    current_streak: int = 0
    recent_achievements: list[Achievement] = []
    strength_areas: list[Topic] = []
    growth_areas: list[Topic] = []
