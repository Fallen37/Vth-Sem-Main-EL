"""Learning Profile model - SQLAlchemy and Pydantic schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.sqlite import JSON

from src.models.database import Base
from src.models.enums import InteractionSpeed, FontSize


# Pydantic schemas for nested JSON fields
class OutputMode(BaseModel):
    """Output mode preferences."""

    text: bool = True
    audio: bool = False
    visual: bool = False


class ExplanationStyle(BaseModel):
    """Explanation style preferences."""

    use_examples: bool = True
    use_diagrams: bool = True
    use_analogies: bool = True
    simplify_language: bool = False
    step_by_step: bool = True


class InterfacePreferences(BaseModel):
    """Interface customization preferences."""

    dark_mode: bool = False
    font_size: FontSize = FontSize.MEDIUM
    reduced_motion: bool = False
    high_contrast: bool = False


class TopicComprehension(BaseModel):
    """Comprehension pattern for a topic."""

    topic_id: str
    topic_name: str
    comprehension_level: float = Field(ge=0.0, le=1.0)
    interaction_count: int = 0
    last_interaction: Optional[datetime] = None


# SQLAlchemy Model
class LearningProfileORM(Base):
    """SQLAlchemy Learning Profile model."""

    __tablename__ = "learning_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), unique=True, nullable=False
    )
    preferred_output_mode: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=lambda: OutputMode().model_dump()
    )
    preferred_explanation_style: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=lambda: ExplanationStyle().model_dump()
    )
    interaction_speed: Mapped[str] = mapped_column(
        String(20), nullable=False, default=InteractionSpeed.MEDIUM.value
    )
    interface_preferences: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=lambda: InterfacePreferences().model_dump()
    )
    comprehension_history: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    user = relationship("UserORM", back_populates="learning_profile")


# Pydantic Schemas
class LearningProfileBase(BaseModel):
    """Base learning profile schema."""

    preferred_output_mode: OutputMode = Field(default_factory=OutputMode)
    preferred_explanation_style: ExplanationStyle = Field(default_factory=ExplanationStyle)
    interaction_speed: InteractionSpeed = InteractionSpeed.MEDIUM
    interface_preferences: InterfacePreferences = Field(default_factory=InterfacePreferences)


class LearningProfileCreate(LearningProfileBase):
    """Schema for creating a learning profile."""

    user_id: UUID


class LearningProfileUpdate(BaseModel):
    """Schema for updating a learning profile."""

    preferred_output_mode: Optional[OutputMode] = None
    preferred_explanation_style: Optional[ExplanationStyle] = None
    interaction_speed: Optional[InteractionSpeed] = None
    interface_preferences: Optional[InterfacePreferences] = None


class LearningProfile(LearningProfileBase):
    """Full learning profile schema."""

    id: UUID
    user_id: UUID
    comprehension_history: list[TopicComprehension] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
