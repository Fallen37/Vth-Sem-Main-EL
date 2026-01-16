"""Profile API endpoints for managing learning profiles."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db_session, require_current_user
from src.models.user import UserORM
from src.models.learning_profile import (
    LearningProfile,
    LearningProfileUpdate,
    OutputMode,
    ExplanationStyle,
    InterfacePreferences,
    TopicComprehension,
)
from src.models.enums import InteractionSpeed
from src.services.profile_service import ProfileService


router = APIRouter(prefix="/profile", tags=["Profile"])


class ProfileResponse(BaseModel):
    """Response model for learning profile."""
    
    id: UUID
    user_id: UUID
    preferred_output_mode: OutputMode
    preferred_explanation_style: ExplanationStyle
    interaction_speed: InteractionSpeed
    interface_preferences: InterfacePreferences
    comprehension_history: list[TopicComprehension]


class UpdateProfileRequest(BaseModel):
    """Request model for updating profile."""
    
    preferred_output_mode: Optional[OutputMode] = None
    preferred_explanation_style: Optional[ExplanationStyle] = None
    interaction_speed: Optional[InteractionSpeed] = None
    interface_preferences: Optional[InterfacePreferences] = None


class SessionPreferencesResponse(BaseModel):
    """Response model for session preferences."""
    
    output_mode: OutputMode
    explanation_style: ExplanationStyle
    interaction_speed: InteractionSpeed
    interface_preferences: InterfacePreferences


@router.get("", response_model=ProfileResponse)
async def get_profile(
    user: UserORM = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ProfileResponse:
    """Get the current user's learning profile."""
    user_id = UUID(user.id)
    
    profile_service = ProfileService(db)
    profile = await profile_service.get_or_create_profile(user_id)
    
    return ProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        preferred_output_mode=profile.preferred_output_mode,
        preferred_explanation_style=profile.preferred_explanation_style,
        interaction_speed=profile.interaction_speed,
        interface_preferences=profile.interface_preferences,
        comprehension_history=profile.comprehension_history,
    )


@router.put("", response_model=ProfileResponse)
async def update_profile(
    request: UpdateProfileRequest,
    user: UserORM = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ProfileResponse:
    """Update the current user's learning profile."""
    user_id = UUID(user.id)
    
    profile_service = ProfileService(db)
    
    # Ensure profile exists
    await profile_service.get_or_create_profile(user_id)
    
    # Update profile
    updates = LearningProfileUpdate(
        preferred_output_mode=request.preferred_output_mode,
        preferred_explanation_style=request.preferred_explanation_style,
        interaction_speed=request.interaction_speed,
        interface_preferences=request.interface_preferences,
    )
    
    profile = await profile_service.update_profile(user_id, updates)
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )
    
    return ProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        preferred_output_mode=profile.preferred_output_mode,
        preferred_explanation_style=profile.preferred_explanation_style,
        interaction_speed=profile.interaction_speed,
        interface_preferences=profile.interface_preferences,
        comprehension_history=profile.comprehension_history,
    )


@router.get("/output-mode", response_model=OutputMode)
async def get_output_mode(
    user: UserORM = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> OutputMode:
    """Get the user's preferred output mode."""
    user_id = UUID(user.id)
    
    profile_service = ProfileService(db)
    return await profile_service.get_preferred_output_mode(user_id)


@router.get("/explanation-style", response_model=ExplanationStyle)
async def get_explanation_style(
    user: UserORM = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ExplanationStyle:
    """Get the user's preferred explanation style."""
    user_id = UUID(user.id)
    
    profile_service = ProfileService(db)
    return await profile_service.get_preferred_explanation_style(user_id)


@router.get("/comprehension", response_model=list[TopicComprehension])
async def get_comprehension_patterns(
    user: UserORM = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> list[TopicComprehension]:
    """Get the user's comprehension patterns across topics."""
    user_id = UUID(user.id)
    
    profile_service = ProfileService(db)
    return await profile_service.get_comprehension_patterns(user_id)


@router.get("/comprehension/{topic_id}", response_model=Optional[TopicComprehension])
async def get_topic_comprehension(
    topic_id: str,
    user: UserORM = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> Optional[TopicComprehension]:
    """Get comprehension data for a specific topic."""
    user_id = UUID(user.id)
    
    profile_service = ProfileService(db)
    return await profile_service.get_topic_comprehension(user_id, topic_id)


@router.get("/session-preferences", response_model=SessionPreferencesResponse)
async def get_session_preferences(
    user: UserORM = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> SessionPreferencesResponse:
    """Get all preferences needed to initialize a new session."""
    user_id = UUID(user.id)
    
    profile_service = ProfileService(db)
    preferences = await profile_service.initialize_session_preferences(user_id)
    
    return SessionPreferencesResponse(
        output_mode=preferences["output_mode"],
        explanation_style=preferences["explanation_style"],
        interaction_speed=preferences["interaction_speed"],
        interface_preferences=preferences["interface_preferences"],
    )
