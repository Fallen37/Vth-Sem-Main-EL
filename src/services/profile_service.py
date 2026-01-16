"""Profile Service - manages learning profiles and preference adaptation."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.learning_profile import (
    LearningProfile,
    LearningProfileCreate,
    LearningProfileORM,
    LearningProfileUpdate,
    OutputMode,
    ExplanationStyle,
    InterfacePreferences,
    TopicComprehension,
)
from src.models.enums import (
    InteractionSpeed,
    InputType,
    ComprehensionLevel,
)
from src.models.user import UserORM


class Interaction(BaseModel):
    """Represents a user interaction for profile learning."""

    input_type: InputType
    topic_id: Optional[str] = None
    topic_name: Optional[str] = None
    comprehension_feedback: Optional[ComprehensionLevel] = None
    output_mode_used: Optional[OutputMode] = None
    response_time_ms: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ProfileService:
    """Service for managing learning profiles and preference adaptation."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_profile(self, user_id: UUID) -> Optional[LearningProfile]:
        """
        Get a user's learning profile.

        Args:
            user_id: The user's ID

        Returns:
            LearningProfile if found, None otherwise
        """
        result = await self.db.execute(
            select(LearningProfileORM).where(
                LearningProfileORM.user_id == str(user_id)
            )
        )
        profile_orm = result.scalar_one_or_none()

        if not profile_orm:
            return None

        return self._orm_to_pydantic(profile_orm)

    async def get_or_create_profile(self, user_id: UUID) -> LearningProfile:
        """
        Get a user's learning profile, creating one with defaults if it doesn't exist.

        Args:
            user_id: The user's ID

        Returns:
            LearningProfile (existing or newly created)
        """
        profile = await self.get_profile(user_id)
        if profile:
            return profile

        # Verify user exists
        user_result = await self.db.execute(
            select(UserORM).where(UserORM.id == str(user_id))
        )
        user = user_result.scalar_one_or_none()
        if not user:
            raise ValueError(f"User {user_id} not found")

        # Create default profile
        profile_id = str(uuid4())
        profile_orm = LearningProfileORM(
            id=profile_id,
            user_id=str(user_id),
            preferred_output_mode=OutputMode().model_dump(),
            preferred_explanation_style=ExplanationStyle().model_dump(),
            interaction_speed=InteractionSpeed.MEDIUM.value,
            interface_preferences=InterfacePreferences().model_dump(),
            comprehension_history=[],
        )

        self.db.add(profile_orm)
        await self.db.commit()
        await self.db.refresh(profile_orm)

        return self._orm_to_pydantic(profile_orm)

    async def update_profile(
        self, user_id: UUID, updates: LearningProfileUpdate
    ) -> Optional[LearningProfile]:
        """
        Update a user's learning profile.

        Args:
            user_id: The user's ID
            updates: Profile updates to apply

        Returns:
            Updated LearningProfile if found, None otherwise
        """
        result = await self.db.execute(
            select(LearningProfileORM).where(
                LearningProfileORM.user_id == str(user_id)
            )
        )
        profile_orm = result.scalar_one_or_none()

        if not profile_orm:
            return None

        # Apply updates
        if updates.preferred_output_mode is not None:
            profile_orm.preferred_output_mode = updates.preferred_output_mode.model_dump()

        if updates.preferred_explanation_style is not None:
            profile_orm.preferred_explanation_style = (
                updates.preferred_explanation_style.model_dump()
            )

        if updates.interaction_speed is not None:
            profile_orm.interaction_speed = updates.interaction_speed.value

        if updates.interface_preferences is not None:
            profile_orm.interface_preferences = (
                updates.interface_preferences.model_dump()
            )

        profile_orm.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(profile_orm)

        return self._orm_to_pydantic(profile_orm)


    async def record_interaction(
        self, user_id: UUID, interaction: Interaction
    ) -> LearningProfile:
        """
        Record an interaction and update the learning profile based on observed behavior.

        This method updates the profile to reflect:
        - Output mode usage patterns
        - Comprehension feedback patterns per topic
        - Interaction timing patterns

        Args:
            user_id: The user's ID
            interaction: The interaction to record

        Returns:
            Updated LearningProfile

        Requirements: 2.2 - Continuously update Learning_Profile based on observed behavior
        """
        profile = await self.get_or_create_profile(user_id)

        result = await self.db.execute(
            select(LearningProfileORM).where(
                LearningProfileORM.user_id == str(user_id)
            )
        )
        profile_orm = result.scalar_one_or_none()

        if not profile_orm:
            raise ValueError(f"Profile for user {user_id} not found")

        # Update output mode preferences based on usage
        if interaction.output_mode_used:
            current_mode = OutputMode(**profile_orm.preferred_output_mode)
            # Reinforce the modes that were used
            if interaction.output_mode_used.text:
                current_mode.text = True
            if interaction.output_mode_used.audio:
                current_mode.audio = True
            if interaction.output_mode_used.visual:
                current_mode.visual = True
            profile_orm.preferred_output_mode = current_mode.model_dump()

        # Update comprehension history for the topic
        if interaction.topic_id and interaction.comprehension_feedback:
            # Make a deep copy of the comprehension history to ensure SQLAlchemy detects changes
            comprehension_history = [dict(entry) for entry in (profile_orm.comprehension_history or [])]
            
            # Find existing topic entry or create new one
            topic_entry = None
            topic_index = None
            for i, entry in enumerate(comprehension_history):
                if entry.get("topic_id") == interaction.topic_id:
                    topic_entry = dict(entry)  # Make a copy
                    topic_index = i
                    break

            # Calculate comprehension level from feedback
            feedback_to_level = {
                ComprehensionLevel.UNDERSTOOD: 1.0,
                ComprehensionLevel.PARTIAL: 0.5,
                ComprehensionLevel.NOT_UNDERSTOOD: 0.0,
            }
            new_level = feedback_to_level.get(interaction.comprehension_feedback, 0.5)

            if topic_entry is not None and topic_index is not None:
                # Update existing entry with weighted average
                old_level = topic_entry.get("comprehension_level", 0.5)
                old_count = topic_entry.get("interaction_count", 1)
                # Weighted average favoring recent interactions
                updated_level = (old_level * old_count + new_level * 2) / (old_count + 2)
                
                topic_entry["comprehension_level"] = round(updated_level, 3)
                topic_entry["interaction_count"] = old_count + 1
                topic_entry["last_interaction"] = interaction.timestamp.isoformat()
                comprehension_history[topic_index] = topic_entry
            else:
                # Create new topic entry
                new_entry = {
                    "topic_id": interaction.topic_id,
                    "topic_name": interaction.topic_name or interaction.topic_id,
                    "comprehension_level": new_level,
                    "interaction_count": 1,
                    "last_interaction": interaction.timestamp.isoformat(),
                }
                comprehension_history.append(new_entry)

            # Assign a new list to ensure SQLAlchemy detects the change
            profile_orm.comprehension_history = comprehension_history

        # Update interaction speed based on response time
        if interaction.response_time_ms is not None:
            # Adjust speed preference based on response patterns
            # Fast: < 3000ms, Medium: 3000-8000ms, Slow: > 8000ms
            if interaction.response_time_ms < 3000:
                profile_orm.interaction_speed = InteractionSpeed.FAST.value
            elif interaction.response_time_ms > 8000:
                profile_orm.interaction_speed = InteractionSpeed.SLOW.value
            else:
                profile_orm.interaction_speed = InteractionSpeed.MEDIUM.value

        profile_orm.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(profile_orm)

        return self._orm_to_pydantic(profile_orm)

    async def get_preferred_output_mode(self, user_id: UUID) -> OutputMode:
        """
        Get the user's preferred output mode.

        Args:
            user_id: The user's ID

        Returns:
            OutputMode preferences

        Requirements: 2.1, 2.3 - Track and apply stored preferences
        """
        profile = await self.get_or_create_profile(user_id)
        return profile.preferred_output_mode

    async def get_preferred_explanation_style(self, user_id: UUID) -> ExplanationStyle:
        """
        Get the user's preferred explanation style.

        Args:
            user_id: The user's ID

        Returns:
            ExplanationStyle preferences

        Requirements: 2.4 - Store preferred explanation styles
        """
        profile = await self.get_or_create_profile(user_id)
        return profile.preferred_explanation_style

    async def get_comprehension_patterns(
        self, user_id: UUID
    ) -> list[TopicComprehension]:
        """
        Get the user's comprehension patterns across topics.

        Args:
            user_id: The user's ID

        Returns:
            List of TopicComprehension records
        """
        profile = await self.get_or_create_profile(user_id)
        return profile.comprehension_history

    async def get_topic_comprehension(
        self, user_id: UUID, topic_id: str
    ) -> Optional[TopicComprehension]:
        """
        Get comprehension data for a specific topic.

        Args:
            user_id: The user's ID
            topic_id: The topic ID

        Returns:
            TopicComprehension if found, None otherwise
        """
        patterns = await self.get_comprehension_patterns(user_id)
        for pattern in patterns:
            if pattern.topic_id == topic_id:
                return pattern
        return None

    async def initialize_session_preferences(self, user_id: UUID) -> dict:
        """
        Get all preferences needed to initialize a new session.

        This method returns all stored preferences that should be applied
        when a new session begins.

        Args:
            user_id: The user's ID

        Returns:
            Dictionary with all session preferences

        Requirements: 2.3 - Apply stored preferences from Learning_Profile automatically
        """
        profile = await self.get_or_create_profile(user_id)

        return {
            "output_mode": profile.preferred_output_mode,
            "explanation_style": profile.preferred_explanation_style,
            "interaction_speed": profile.interaction_speed,
            "interface_preferences": profile.interface_preferences,
        }

    def _orm_to_pydantic(self, profile_orm: LearningProfileORM) -> LearningProfile:
        """Convert ORM model to Pydantic model."""
        # Parse comprehension history
        comprehension_history = []
        for entry in profile_orm.comprehension_history or []:
            try:
                # Handle datetime parsing
                last_interaction = entry.get("last_interaction")
                if isinstance(last_interaction, str):
                    last_interaction = datetime.fromisoformat(last_interaction)
                
                comprehension_history.append(
                    TopicComprehension(
                        topic_id=entry["topic_id"],
                        topic_name=entry.get("topic_name", entry["topic_id"]),
                        comprehension_level=entry.get("comprehension_level", 0.5),
                        interaction_count=entry.get("interaction_count", 0),
                        last_interaction=last_interaction,
                    )
                )
            except (KeyError, ValueError):
                continue

        return LearningProfile(
            id=UUID(profile_orm.id),
            user_id=UUID(profile_orm.user_id),
            preferred_output_mode=OutputMode(**profile_orm.preferred_output_mode),
            preferred_explanation_style=ExplanationStyle(
                **profile_orm.preferred_explanation_style
            ),
            interaction_speed=InteractionSpeed(profile_orm.interaction_speed),
            interface_preferences=InterfacePreferences(
                **profile_orm.interface_preferences
            ),
            comprehension_history=comprehension_history,
            created_at=profile_orm.created_at,
            updated_at=profile_orm.updated_at,
        )
