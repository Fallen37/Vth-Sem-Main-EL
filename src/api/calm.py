"""Calm Mode API endpoints for break and emergency features."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db_session, require_current_user
from src.models.user import UserORM
from src.services.calm_mode import (
    CalmModeService,
    BreakSession,
    BreathingSession,
    BreathingPattern,
    AudioStream,
    CalmingContent,
)
from src.services.guardian_service import GuardianService


router = APIRouter(prefix="/calm", tags=["Calm Mode"])


class BreakSessionResponse(BaseModel):
    """Response model for break session."""
    
    session_id: str
    user_id: UUID
    started_at: str
    breathing_exercise_active: bool
    music_playing: bool
    is_emergency: bool
    is_active: bool


class BreathingSessionResponse(BaseModel):
    """Response model for breathing session."""
    
    session_id: str
    user_id: UUID
    pattern: str
    current_phase: str
    remaining_cycles: int
    phase_duration_seconds: int


class AudioStreamResponse(BaseModel):
    """Response model for audio stream."""
    
    stream_id: str
    user_id: UUID
    audio_url: str
    audio_type: str
    is_playing: bool


class StartBreathingRequest(BaseModel):
    """Request model for starting breathing exercise."""
    
    pattern: BreathingPattern = BreathingPattern.BOX_BREATHING
    cycles: int = Field(4, ge=1, le=10)


class PlayMusicRequest(BaseModel):
    """Request model for playing calming music."""
    
    track_id: Optional[str] = None


class EmergencyResponse(BaseModel):
    """Response model for emergency alert."""
    
    calming_content: dict
    guardian_alerted: bool


class MusicTrackResponse(BaseModel):
    """Response model for music track."""
    
    id: str
    url: str
    name: str


class BreathingPatternResponse(BaseModel):
    """Response model for breathing pattern."""
    
    id: str
    name: str
    description: str


@router.post("/break/start", response_model=BreakSessionResponse)
async def start_break(
    user: UserORM = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> BreakSessionResponse:
    """
    Start a break session, pausing the learning session.
    
    Requirements: 9.1, 9.2 - Provide break button and pause session
    """
    user_id = UUID(user.id)
    
    guardian_service = GuardianService(db)
    service = CalmModeService(db=db, guardian_service=guardian_service)
    
    break_session = await service.activate_break(user_id)
    
    return BreakSessionResponse(
        session_id=break_session.session_id,
        user_id=break_session.user_id,
        started_at=break_session.started_at.isoformat(),
        breathing_exercise_active=break_session.breathing_exercise_active,
        music_playing=break_session.music_playing,
        is_emergency=break_session.is_emergency,
        is_active=break_session.is_active,
    )


@router.post("/break/end")
async def end_break(
    user: UserORM = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    End the break session and resume learning.
    
    Requirements: 9.2 - Resume session after break
    """
    user_id = UUID(user.id)
    
    service = CalmModeService(db=db)
    ended = await service.end_break(user_id)
    
    if not ended:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active break session found",
        )
    
    return {"message": "Break ended, ready to continue learning"}


@router.get("/break/status", response_model=Optional[BreakSessionResponse])
async def get_break_status(
    user: UserORM = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> Optional[BreakSessionResponse]:
    """Get the current break status."""
    user_id = UUID(user.id)
    
    service = CalmModeService(db=db)
    break_session = await service.get_break_status(user_id)
    
    if not break_session:
        return None
    
    return BreakSessionResponse(
        session_id=break_session.session_id,
        user_id=break_session.user_id,
        started_at=break_session.started_at.isoformat(),
        breathing_exercise_active=break_session.breathing_exercise_active,
        music_playing=break_session.music_playing,
        is_emergency=break_session.is_emergency,
        is_active=break_session.is_active,
    )


@router.post("/breathing/start", response_model=BreathingSessionResponse)
async def start_breathing_exercise(
    request: StartBreathingRequest,
    user: UserORM = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> BreathingSessionResponse:
    """
    Start a guided breathing exercise.
    
    Requirements: 9.3 - Offer guided breathing exercise option
    """
    user_id = UUID(user.id)
    
    service = CalmModeService(db=db)
    breathing_session = await service.start_breathing_exercise(
        user_id=user_id,
        pattern=request.pattern,
        cycles=request.cycles,
    )
    
    return BreathingSessionResponse(
        session_id=breathing_session.session_id,
        user_id=breathing_session.user_id,
        pattern=breathing_session.pattern.value,
        current_phase=breathing_session.current_phase.value,
        remaining_cycles=breathing_session.remaining_cycles,
        phase_duration_seconds=breathing_session.get_phase_duration_seconds(),
    )


@router.post("/breathing/advance", response_model=Optional[BreathingSessionResponse])
async def advance_breathing_phase(
    user: UserORM = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> Optional[BreathingSessionResponse]:
    """
    Advance to the next phase of the breathing exercise.
    
    Returns None if the exercise is complete.
    """
    user_id = UUID(user.id)
    
    service = CalmModeService(db=db)
    breathing_session = await service.advance_breathing_phase(user_id)
    
    if not breathing_session:
        return None
    
    return BreathingSessionResponse(
        session_id=breathing_session.session_id,
        user_id=breathing_session.user_id,
        pattern=breathing_session.pattern.value,
        current_phase=breathing_session.current_phase.value,
        remaining_cycles=breathing_session.remaining_cycles,
        phase_duration_seconds=breathing_session.get_phase_duration_seconds(),
    )


@router.post("/breathing/stop")
async def stop_breathing_exercise(
    user: UserORM = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Stop the breathing exercise."""
    user_id = UUID(user.id)
    
    service = CalmModeService(db=db)
    stopped = await service.stop_breathing_exercise(user_id)
    
    if not stopped:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active breathing exercise found",
        )
    
    return {"message": "Breathing exercise stopped"}


@router.get("/breathing/status", response_model=Optional[BreathingSessionResponse])
async def get_breathing_status(
    user: UserORM = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> Optional[BreathingSessionResponse]:
    """Get the current breathing exercise status."""
    user_id = UUID(user.id)
    
    service = CalmModeService(db=db)
    breathing_session = await service.get_breathing_status(user_id)
    
    if not breathing_session:
        return None
    
    return BreathingSessionResponse(
        session_id=breathing_session.session_id,
        user_id=breathing_session.user_id,
        pattern=breathing_session.pattern.value,
        current_phase=breathing_session.current_phase.value,
        remaining_cycles=breathing_session.remaining_cycles,
        phase_duration_seconds=breathing_session.get_phase_duration_seconds(),
    )


@router.post("/music/play", response_model=AudioStreamResponse)
async def play_calming_music(
    request: PlayMusicRequest,
    user: UserORM = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> AudioStreamResponse:
    """
    Start playing calming background music.
    
    Requirements: 9.4 - Offer calming background music during breaks
    """
    user_id = UUID(user.id)
    
    service = CalmModeService(db=db)
    audio_stream = await service.play_calm_music(user_id, request.track_id)
    
    return AudioStreamResponse(
        stream_id=audio_stream.stream_id,
        user_id=audio_stream.user_id,
        audio_url=audio_stream.audio_url,
        audio_type=audio_stream.audio_type,
        is_playing=audio_stream.is_playing,
    )


@router.post("/music/stop")
async def stop_calming_music(
    user: UserORM = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Stop playing calming music."""
    user_id = UUID(user.id)
    
    service = CalmModeService(db=db)
    stopped = await service.stop_calm_music(user_id)
    
    if not stopped:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No music currently playing",
        )
    
    return {"message": "Music stopped"}


@router.post("/emergency", response_model=EmergencyResponse)
async def trigger_emergency(
    user: UserORM = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> EmergencyResponse:
    """
    Trigger emergency alert - display calming content and alert guardian.
    
    Requirements: 9.5, 9.6 - Emergency button and alert guardian
    """
    user_id = UUID(user.id)
    
    guardian_service = GuardianService(db)
    service = CalmModeService(db=db, guardian_service=guardian_service)
    
    calming_content, guardian_alerted = await service.trigger_emergency_alert(user_id)
    
    return EmergencyResponse(
        calming_content={
            "message": calming_content.message,
            "breathing_prompt": calming_content.breathing_prompt,
            "visual_url": calming_content.visual_url,
            "audio_url": calming_content.audio_url,
        },
        guardian_alerted=guardian_alerted,
    )


@router.get("/music/tracks", response_model=list[MusicTrackResponse])
async def get_available_music_tracks(
    user: UserORM = Depends(require_current_user),
) -> list[MusicTrackResponse]:
    """Get list of available calming music tracks."""
    service = CalmModeService()
    tracks = service.get_available_music_tracks()
    
    return [
        MusicTrackResponse(
            id=t["id"],
            url=t["url"],
            name=t["name"],
        )
        for t in tracks
    ]


@router.get("/breathing/patterns", response_model=list[BreathingPatternResponse])
async def get_available_breathing_patterns(
    user: UserORM = Depends(require_current_user),
) -> list[BreathingPatternResponse]:
    """Get list of available breathing patterns."""
    service = CalmModeService()
    patterns = service.get_available_breathing_patterns()
    
    return [
        BreathingPatternResponse(
            id=p["id"],
            name=p["name"],
            description=p["description"],
        )
        for p in patterns
    ]


@router.get("/is-paused")
async def check_session_paused(
    user: UserORM = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Check if the user's learning session is paused due to break mode."""
    user_id = UUID(user.id)
    
    service = CalmModeService(db=db)
    is_paused = await service.is_session_paused(user_id)
    
    return {"is_paused": is_paused}
