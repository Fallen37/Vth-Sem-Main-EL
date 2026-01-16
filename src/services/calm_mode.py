"""Calm Mode Service - handles sensory regulation features.

Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6
- Provide visible "Take a Break" button accessible at all times
- Pause learning session when break mode is activated
- Offer guided breathing exercise option
- Offer calming background music during breaks
- Provide "I need help" emergency button for panic situations
- Display calming content and alert guardian on emergency
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.session import SessionORM
from src.models.user import UserORM
from src.services.guardian_service import GuardianService, AlertType


class BreathingPattern(str, Enum):
    """Breathing exercise patterns."""
    
    BOX_BREATHING = "box_breathing"  # 4-4-4-4 pattern
    FOUR_SEVEN_EIGHT = "4_7_8"  # 4-7-8 pattern
    SIMPLE = "simple"  # Simple in-out pattern


class BreathingPhase(str, Enum):
    """Current phase of breathing exercise."""
    
    INHALE = "inhale"
    HOLD = "hold"
    EXHALE = "exhale"
    REST = "rest"


class BreakSession(BaseModel):
    """Represents an active break session.
    
    Requirements: 9.2 - Pause learning session when break mode is activated
    """
    
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: UUID
    started_at: datetime = Field(default_factory=datetime.utcnow)
    breathing_exercise_active: bool = False
    music_playing: bool = False
    is_emergency: bool = False
    ended_at: Optional[datetime] = None
    
    @property
    def is_active(self) -> bool:
        """Check if the break session is still active."""
        return self.ended_at is None


class BreathingSession(BaseModel):
    """Represents an active breathing exercise session.
    
    Requirements: 9.3 - Offer guided breathing exercise option
    """
    
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: UUID
    pattern: BreathingPattern = BreathingPattern.BOX_BREATHING
    current_phase: BreathingPhase = BreathingPhase.INHALE
    remaining_cycles: int = 4
    started_at: datetime = Field(default_factory=datetime.utcnow)
    
    def get_phase_duration_seconds(self) -> int:
        """Get the duration in seconds for the current phase based on pattern."""
        if self.pattern == BreathingPattern.BOX_BREATHING:
            # 4-4-4-4 pattern: 4 seconds each phase
            return 4
        elif self.pattern == BreathingPattern.FOUR_SEVEN_EIGHT:
            # 4-7-8 pattern
            durations = {
                BreathingPhase.INHALE: 4,
                BreathingPhase.HOLD: 7,
                BreathingPhase.EXHALE: 8,
                BreathingPhase.REST: 0,
            }
            return durations.get(self.current_phase, 4)
        else:
            # Simple pattern: 4 seconds in, 4 seconds out
            return 4
    
    def advance_phase(self) -> "BreathingSession":
        """Advance to the next phase of the breathing exercise."""
        phase_order = [
            BreathingPhase.INHALE,
            BreathingPhase.HOLD,
            BreathingPhase.EXHALE,
            BreathingPhase.REST,
        ]
        
        current_index = phase_order.index(self.current_phase)
        next_index = (current_index + 1) % len(phase_order)
        
        # If we completed a full cycle (back to INHALE), decrement remaining cycles
        if next_index == 0:
            self.remaining_cycles = max(0, self.remaining_cycles - 1)
        
        self.current_phase = phase_order[next_index]
        return self


class AudioStream(BaseModel):
    """Represents a calming audio stream.
    
    Requirements: 9.4 - Offer calming background music during breaks
    """
    
    stream_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: UUID
    audio_url: str
    audio_type: str = "calming_music"
    is_playing: bool = True
    started_at: datetime = Field(default_factory=datetime.utcnow)


class CalmingContent(BaseModel):
    """Calming content displayed during emergency situations.
    
    Requirements: 9.6 - Display calming content on emergency
    """
    
    message: str
    breathing_prompt: Optional[str] = None
    visual_url: Optional[str] = None
    audio_url: Optional[str] = None


# Default calming content for emergency situations
DEFAULT_CALMING_CONTENT = CalmingContent(
    message="You're safe. Take a deep breath. Everything is okay.",
    breathing_prompt="Breathe in slowly... hold... breathe out slowly...",
    visual_url="/assets/calming/peaceful-nature.jpg",
    audio_url="/assets/audio/gentle-waves.mp3",
)

# Available calming music tracks
CALMING_MUSIC_TRACKS = [
    {"id": "gentle-waves", "url": "/assets/audio/gentle-waves.mp3", "name": "Gentle Waves"},
    {"id": "forest-sounds", "url": "/assets/audio/forest-sounds.mp3", "name": "Forest Sounds"},
    {"id": "soft-piano", "url": "/assets/audio/soft-piano.mp3", "name": "Soft Piano"},
    {"id": "rain-sounds", "url": "/assets/audio/rain-sounds.mp3", "name": "Rain Sounds"},
]


class CalmModeService:
    """Service for managing calm mode and sensory regulation features.
    
    Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6
    """

    def __init__(
        self,
        db: Optional[AsyncSession] = None,
        guardian_service: Optional[GuardianService] = None,
    ):
        self.db = db
        self.guardian_service = guardian_service
        
        # In-memory storage for active break sessions
        # In production, this would be stored in Redis or database
        self._active_breaks: dict[str, BreakSession] = {}
        self._breathing_sessions: dict[str, BreathingSession] = {}
        self._audio_streams: dict[str, AudioStream] = {}
        
        # Track paused learning sessions
        self._paused_sessions: dict[str, str] = {}  # user_id -> learning_session_id

    async def activate_break(self, user_id: UUID) -> BreakSession:
        """
        Activate break mode for a user, pausing their learning session.

        Args:
            user_id: The user's ID

        Returns:
            BreakSession with break state information

        Requirements: 9.1, 9.2 - Provide break button and pause session
        """
        user_id_str = str(user_id)
        
        # Check if user already has an active break
        if user_id_str in self._active_breaks:
            existing_break = self._active_breaks[user_id_str]
            if existing_break.is_active:
                return existing_break
        
        # Pause any active learning session
        await self._pause_learning_session(user_id)
        
        # Create new break session
        break_session = BreakSession(user_id=user_id)
        self._active_breaks[user_id_str] = break_session
        
        return break_session

    async def _pause_learning_session(self, user_id: UUID) -> Optional[str]:
        """
        Pause the user's active learning session.

        Args:
            user_id: The user's ID

        Returns:
            The paused session ID if found

        Requirements: 9.2 - Pause learning session when break mode is activated
        """
        if not self.db:
            return None
        
        user_id_str = str(user_id)
        
        # Find active session (one without ended_at)
        result = await self.db.execute(
            select(SessionORM).where(
                SessionORM.user_id == user_id_str,
                SessionORM.ended_at.is_(None),
            )
        )
        session = result.scalar_one_or_none()
        
        if session:
            # Store the paused session reference
            self._paused_sessions[user_id_str] = session.id
            return session.id
        
        return None

    async def start_breathing_exercise(
        self,
        user_id: UUID,
        pattern: BreathingPattern = BreathingPattern.BOX_BREATHING,
        cycles: int = 4,
    ) -> BreathingSession:
        """
        Start a guided breathing exercise for the user.

        Args:
            user_id: The user's ID
            pattern: The breathing pattern to use
            cycles: Number of breathing cycles

        Returns:
            BreathingSession with exercise state

        Requirements: 9.3 - Offer guided breathing exercise option
        """
        user_id_str = str(user_id)
        
        # Ensure user has an active break
        if user_id_str not in self._active_breaks:
            await self.activate_break(user_id)
        
        # Create breathing session
        breathing_session = BreathingSession(
            user_id=user_id,
            pattern=pattern,
            remaining_cycles=cycles,
        )
        
        self._breathing_sessions[user_id_str] = breathing_session
        
        # Update break session to indicate breathing exercise is active
        if user_id_str in self._active_breaks:
            self._active_breaks[user_id_str].breathing_exercise_active = True
        
        return breathing_session

    async def advance_breathing_phase(self, user_id: UUID) -> Optional[BreathingSession]:
        """
        Advance to the next phase of the breathing exercise.

        Args:
            user_id: The user's ID

        Returns:
            Updated BreathingSession or None if no active session
        """
        user_id_str = str(user_id)
        
        if user_id_str not in self._breathing_sessions:
            return None
        
        session = self._breathing_sessions[user_id_str]
        session.advance_phase()
        
        # If cycles are complete, end the breathing session
        if session.remaining_cycles == 0 and session.current_phase == BreathingPhase.INHALE:
            await self.stop_breathing_exercise(user_id)
            return None
        
        return session

    async def stop_breathing_exercise(self, user_id: UUID) -> bool:
        """
        Stop the breathing exercise for a user.

        Args:
            user_id: The user's ID

        Returns:
            True if exercise was stopped
        """
        user_id_str = str(user_id)
        
        if user_id_str in self._breathing_sessions:
            del self._breathing_sessions[user_id_str]
            
            # Update break session
            if user_id_str in self._active_breaks:
                self._active_breaks[user_id_str].breathing_exercise_active = False
            
            return True
        
        return False

    async def play_calm_music(
        self,
        user_id: UUID,
        track_id: Optional[str] = None,
    ) -> AudioStream:
        """
        Start playing calming background music.

        Args:
            user_id: The user's ID
            track_id: Optional specific track to play

        Returns:
            AudioStream with playback information

        Requirements: 9.4 - Offer calming background music during breaks
        """
        user_id_str = str(user_id)
        
        # Ensure user has an active break
        if user_id_str not in self._active_breaks:
            await self.activate_break(user_id)
        
        # Select track
        if track_id:
            track = next(
                (t for t in CALMING_MUSIC_TRACKS if t["id"] == track_id),
                CALMING_MUSIC_TRACKS[0],
            )
        else:
            track = CALMING_MUSIC_TRACKS[0]
        
        # Create audio stream
        audio_stream = AudioStream(
            user_id=user_id,
            audio_url=track["url"],
        )
        
        self._audio_streams[user_id_str] = audio_stream
        
        # Update break session
        if user_id_str in self._active_breaks:
            self._active_breaks[user_id_str].music_playing = True
        
        return audio_stream

    async def stop_calm_music(self, user_id: UUID) -> bool:
        """
        Stop playing calming music.

        Args:
            user_id: The user's ID

        Returns:
            True if music was stopped
        """
        user_id_str = str(user_id)
        
        if user_id_str in self._audio_streams:
            self._audio_streams[user_id_str].is_playing = False
            del self._audio_streams[user_id_str]
            
            # Update break session
            if user_id_str in self._active_breaks:
                self._active_breaks[user_id_str].music_playing = False
            
            return True
        
        return False

    async def trigger_emergency_alert(
        self,
        user_id: UUID,
    ) -> tuple[CalmingContent, bool]:
        """
        Trigger emergency alert - display calming content and alert guardian.

        Args:
            user_id: The user's ID

        Returns:
            Tuple of (CalmingContent, guardian_alerted: bool)

        Requirements: 9.5, 9.6 - Emergency button and alert guardian
        """
        user_id_str = str(user_id)
        
        # Activate break mode if not already active
        if user_id_str not in self._active_breaks:
            break_session = await self.activate_break(user_id)
        else:
            break_session = self._active_breaks[user_id_str]
        
        # Mark as emergency
        break_session.is_emergency = True
        
        # Start calming music automatically
        await self.play_calm_music(user_id)
        
        # Alert guardian if service is available
        guardian_alerted = False
        if self.guardian_service:
            alert = await self.guardian_service.send_alert(
                student_id=user_id,
                alert_type=AlertType.EMERGENCY,
                message=f"Emergency alert triggered by student. They may need immediate support.",
            )
            guardian_alerted = alert is not None
        
        return DEFAULT_CALMING_CONTENT, guardian_alerted

    async def end_break(self, user_id: UUID) -> bool:
        """
        End break mode and resume the learning session.

        Args:
            user_id: The user's ID

        Returns:
            True if break was ended successfully

        Requirements: 9.2 - Resume session after break
        """
        user_id_str = str(user_id)
        
        if user_id_str not in self._active_breaks:
            return False
        
        # Stop any active breathing exercise
        await self.stop_breathing_exercise(user_id)
        
        # Stop any playing music
        await self.stop_calm_music(user_id)
        
        # Mark break as ended
        break_session = self._active_breaks[user_id_str]
        break_session.ended_at = datetime.utcnow()
        
        # Remove from active breaks
        del self._active_breaks[user_id_str]
        
        # Clear paused session reference
        if user_id_str in self._paused_sessions:
            del self._paused_sessions[user_id_str]
        
        return True

    async def get_break_status(self, user_id: UUID) -> Optional[BreakSession]:
        """
        Get the current break status for a user.

        Args:
            user_id: The user's ID

        Returns:
            BreakSession if user is on break, None otherwise
        """
        user_id_str = str(user_id)
        return self._active_breaks.get(user_id_str)

    async def get_breathing_status(self, user_id: UUID) -> Optional[BreathingSession]:
        """
        Get the current breathing exercise status for a user.

        Args:
            user_id: The user's ID

        Returns:
            BreathingSession if exercise is active, None otherwise
        """
        user_id_str = str(user_id)
        return self._breathing_sessions.get(user_id_str)

    async def is_session_paused(self, user_id: UUID) -> bool:
        """
        Check if the user's learning session is paused due to break mode.

        Args:
            user_id: The user's ID

        Returns:
            True if session is paused

        Requirements: 9.2 - Pause learning session when break mode is activated
        """
        user_id_str = str(user_id)
        
        # Session is paused if user has an active break
        if user_id_str in self._active_breaks:
            return self._active_breaks[user_id_str].is_active
        
        return False

    def get_available_music_tracks(self) -> list[dict]:
        """
        Get list of available calming music tracks.

        Returns:
            List of track information dictionaries
        """
        return CALMING_MUSIC_TRACKS.copy()

    def get_available_breathing_patterns(self) -> list[dict]:
        """
        Get list of available breathing patterns with descriptions.

        Returns:
            List of pattern information dictionaries
        """
        return [
            {
                "id": BreathingPattern.BOX_BREATHING.value,
                "name": "Box Breathing",
                "description": "Breathe in for 4 seconds, hold for 4, breathe out for 4, rest for 4",
            },
            {
                "id": BreathingPattern.FOUR_SEVEN_EIGHT.value,
                "name": "4-7-8 Breathing",
                "description": "Breathe in for 4 seconds, hold for 7, breathe out for 8",
            },
            {
                "id": BreathingPattern.SIMPLE.value,
                "name": "Simple Breathing",
                "description": "Simple in and out breathing, 4 seconds each",
            },
        ]
