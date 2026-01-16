"""Avatar State Service - manages avatar interaction states.

Requirements: 6.1, 6.2, 6.3
- Display an avatar representing the AI tutor
- Student avatar in the interface
- Avatar provides visual feedback during interactions (idle, listening, thinking, explaining states)
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Callable, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class AvatarState(str, Enum):
    """Avatar interaction states.
    
    Requirements: 6.3 - Avatar provides visual feedback during interactions
    """
    
    IDLE = "idle"  # Default state, waiting for interaction
    LISTENING = "listening"  # Processing user input (voice/text being entered)
    THINKING = "thinking"  # Processing query, generating response
    EXPLAINING = "explaining"  # Delivering explanation/response


class AvatarType(str, Enum):
    """Type of avatar in the system.
    
    Requirements: 6.1, 6.2 - AI tutor avatar and student avatar
    """
    
    TUTOR = "tutor"  # AI tutor avatar
    STUDENT = "student"  # Student's avatar


class AvatarConfig(BaseModel):
    """Configuration for an avatar's appearance.
    
    Requirements: 6.1, 6.2 - Avatar representation
    """
    
    avatar_id: str = Field(default_factory=lambda: str(uuid4()))
    avatar_type: AvatarType
    name: str
    image_url: Optional[str] = None
    animation_set: str = "default"  # Animation set to use for state transitions
    
    class Config:
        use_enum_values = True


class AvatarStateChange(BaseModel):
    """Represents a state change event for an avatar.
    
    Requirements: 6.3 - Visual feedback during interactions
    """
    
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: UUID
    avatar_type: AvatarType
    previous_state: AvatarState
    new_state: AvatarState
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict = Field(default_factory=dict)  # Additional context for the state change
    
    class Config:
        use_enum_values = True


class AvatarStatus(BaseModel):
    """Current status of avatars for a user session.
    
    Requirements: 6.1, 6.2, 6.3 - Avatar states and representation
    """
    
    user_id: UUID
    tutor_state: AvatarState = AvatarState.IDLE
    student_state: AvatarState = AvatarState.IDLE
    tutor_config: Optional[AvatarConfig] = None
    student_config: Optional[AvatarConfig] = None
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True


# Type alias for state change callback
StateChangeCallback = Callable[[AvatarStateChange], None]


# Default avatar configurations
DEFAULT_TUTOR_AVATAR = AvatarConfig(
    avatar_type=AvatarType.TUTOR,
    name="Science Buddy",
    image_url="/assets/avatars/tutor-default.png",
    animation_set="friendly",
)

DEFAULT_STUDENT_AVATAR = AvatarConfig(
    avatar_type=AvatarType.STUDENT,
    name="Student",
    image_url="/assets/avatars/student-default.png",
    animation_set="default",
)


class AvatarStateService:
    """Service for managing avatar states and emitting state changes.
    
    Requirements: 6.1, 6.2, 6.3
    - Track interaction states (idle, listening, thinking, explaining)
    - Emit state changes for frontend
    """

    def __init__(self):
        # In-memory storage for avatar states per user
        # In production, this could be stored in Redis for real-time sync
        self._avatar_states: dict[str, AvatarStatus] = {}
        
        # Callbacks for state change notifications (for WebSocket/SSE)
        self._state_change_callbacks: list[StateChangeCallback] = []
        
        # State change history for debugging/analytics
        self._state_history: dict[str, list[AvatarStateChange]] = {}

    def register_callback(self, callback: StateChangeCallback) -> None:
        """
        Register a callback to be notified of state changes.
        
        Args:
            callback: Function to call when state changes occur
        """
        if callback not in self._state_change_callbacks:
            self._state_change_callbacks.append(callback)

    def unregister_callback(self, callback: StateChangeCallback) -> None:
        """
        Unregister a state change callback.
        
        Args:
            callback: The callback to remove
        """
        if callback in self._state_change_callbacks:
            self._state_change_callbacks.remove(callback)

    def _emit_state_change(self, state_change: AvatarStateChange) -> None:
        """
        Emit a state change event to all registered callbacks.
        
        Args:
            state_change: The state change event to emit
        """
        for callback in self._state_change_callbacks:
            try:
                callback(state_change)
            except Exception:
                # Don't let callback errors break the service
                pass

    def _record_state_change(
        self,
        user_id: UUID,
        state_change: AvatarStateChange,
    ) -> None:
        """
        Record a state change in history.
        
        Args:
            user_id: The user's ID
            state_change: The state change to record
        """
        user_id_str = str(user_id)
        if user_id_str not in self._state_history:
            self._state_history[user_id_str] = []
        
        # Keep last 100 state changes per user
        history = self._state_history[user_id_str]
        history.append(state_change)
        if len(history) > 100:
            self._state_history[user_id_str] = history[-100:]

    def initialize_session(
        self,
        user_id: UUID,
        tutor_config: Optional[AvatarConfig] = None,
        student_config: Optional[AvatarConfig] = None,
    ) -> AvatarStatus:
        """
        Initialize avatar states for a new user session.
        
        Args:
            user_id: The user's ID
            tutor_config: Optional custom tutor avatar config
            student_config: Optional custom student avatar config
            
        Returns:
            AvatarStatus with initial states
            
        Requirements: 6.1, 6.2 - Display avatars for tutor and student
        """
        user_id_str = str(user_id)
        
        # Use defaults if not provided
        tutor = tutor_config or DEFAULT_TUTOR_AVATAR.model_copy()
        student = student_config or DEFAULT_STUDENT_AVATAR.model_copy()
        
        status = AvatarStatus(
            user_id=user_id,
            tutor_state=AvatarState.IDLE,
            student_state=AvatarState.IDLE,
            tutor_config=tutor,
            student_config=student,
        )
        
        self._avatar_states[user_id_str] = status
        return status

    def get_status(self, user_id: UUID) -> AvatarStatus:
        """
        Get the current avatar status for a user.
        
        Args:
            user_id: The user's ID
            
        Returns:
            Current AvatarStatus, initializing if needed
        """
        user_id_str = str(user_id)
        
        if user_id_str not in self._avatar_states:
            return self.initialize_session(user_id)
        
        return self._avatar_states[user_id_str]

    def set_tutor_state(
        self,
        user_id: UUID,
        state: AvatarState,
        metadata: Optional[dict] = None,
    ) -> AvatarStateChange:
        """
        Set the tutor avatar state and emit change event.
        
        Args:
            user_id: The user's ID
            state: The new state for the tutor avatar
            metadata: Optional additional context
            
        Returns:
            AvatarStateChange event
            
        Requirements: 6.3 - Avatar provides visual feedback
        """
        user_id_str = str(user_id)
        status = self.get_status(user_id)
        
        previous_state = status.tutor_state
        
        # Create state change event
        state_change = AvatarStateChange(
            user_id=user_id,
            avatar_type=AvatarType.TUTOR,
            previous_state=previous_state,
            new_state=state,
            metadata=metadata or {},
        )
        
        # Update state
        status.tutor_state = state
        status.last_updated = datetime.utcnow()
        self._avatar_states[user_id_str] = status
        
        # Record and emit
        self._record_state_change(user_id, state_change)
        self._emit_state_change(state_change)
        
        return state_change

    def set_student_state(
        self,
        user_id: UUID,
        state: AvatarState,
        metadata: Optional[dict] = None,
    ) -> AvatarStateChange:
        """
        Set the student avatar state and emit change event.
        
        Args:
            user_id: The user's ID
            state: The new state for the student avatar
            metadata: Optional additional context
            
        Returns:
            AvatarStateChange event
            
        Requirements: 6.3 - Avatar provides visual feedback
        """
        user_id_str = str(user_id)
        status = self.get_status(user_id)
        
        previous_state = status.student_state
        
        # Create state change event
        state_change = AvatarStateChange(
            user_id=user_id,
            avatar_type=AvatarType.STUDENT,
            previous_state=previous_state,
            new_state=state,
            metadata=metadata or {},
        )
        
        # Update state
        status.student_state = state
        status.last_updated = datetime.utcnow()
        self._avatar_states[user_id_str] = status
        
        # Record and emit
        self._record_state_change(user_id, state_change)
        self._emit_state_change(state_change)
        
        return state_change

    def transition_to_listening(self, user_id: UUID) -> AvatarStateChange:
        """
        Transition tutor avatar to listening state when user starts input.
        
        Args:
            user_id: The user's ID
            
        Returns:
            AvatarStateChange event
            
        Requirements: 6.3 - Listening state feedback
        """
        return self.set_tutor_state(
            user_id,
            AvatarState.LISTENING,
            metadata={"trigger": "user_input_started"},
        )

    def transition_to_thinking(self, user_id: UUID) -> AvatarStateChange:
        """
        Transition tutor avatar to thinking state when processing query.
        
        Args:
            user_id: The user's ID
            
        Returns:
            AvatarStateChange event
            
        Requirements: 6.3 - Thinking state feedback
        """
        return self.set_tutor_state(
            user_id,
            AvatarState.THINKING,
            metadata={"trigger": "query_processing"},
        )

    def transition_to_explaining(self, user_id: UUID) -> AvatarStateChange:
        """
        Transition tutor avatar to explaining state when delivering response.
        
        Args:
            user_id: The user's ID
            
        Returns:
            AvatarStateChange event
            
        Requirements: 6.3 - Explaining state feedback
        """
        return self.set_tutor_state(
            user_id,
            AvatarState.EXPLAINING,
            metadata={"trigger": "response_delivery"},
        )

    def transition_to_idle(self, user_id: UUID) -> AvatarStateChange:
        """
        Transition tutor avatar to idle state.
        
        Args:
            user_id: The user's ID
            
        Returns:
            AvatarStateChange event
            
        Requirements: 6.3 - Idle state feedback
        """
        return self.set_tutor_state(
            user_id,
            AvatarState.IDLE,
            metadata={"trigger": "interaction_complete"},
        )

    def get_state_history(
        self,
        user_id: UUID,
        limit: int = 50,
    ) -> list[AvatarStateChange]:
        """
        Get recent state change history for a user.
        
        Args:
            user_id: The user's ID
            limit: Maximum number of events to return
            
        Returns:
            List of recent state changes
        """
        user_id_str = str(user_id)
        history = self._state_history.get(user_id_str, [])
        return history[-limit:]

    def clear_session(self, user_id: UUID) -> bool:
        """
        Clear avatar state for a user session.
        
        Args:
            user_id: The user's ID
            
        Returns:
            True if session was cleared
        """
        user_id_str = str(user_id)
        
        if user_id_str in self._avatar_states:
            del self._avatar_states[user_id_str]
            return True
        
        return False

    def update_tutor_config(
        self,
        user_id: UUID,
        config: AvatarConfig,
    ) -> AvatarStatus:
        """
        Update the tutor avatar configuration.
        
        Args:
            user_id: The user's ID
            config: New avatar configuration
            
        Returns:
            Updated AvatarStatus
            
        Requirements: 6.1 - Display avatar representing AI tutor
        """
        status = self.get_status(user_id)
        status.tutor_config = config
        status.last_updated = datetime.utcnow()
        self._avatar_states[str(user_id)] = status
        return status

    def update_student_config(
        self,
        user_id: UUID,
        config: AvatarConfig,
    ) -> AvatarStatus:
        """
        Update the student avatar configuration.
        
        Args:
            user_id: The user's ID
            config: New avatar configuration
            
        Returns:
            Updated AvatarStatus
            
        Requirements: 6.2 - Student avatar in interface
        """
        status = self.get_status(user_id)
        status.student_config = config
        status.last_updated = datetime.utcnow()
        self._avatar_states[str(user_id)] = status
        return status

    def get_available_animation_sets(self) -> list[dict]:
        """
        Get list of available animation sets for avatars.
        
        Returns:
            List of animation set information
        """
        return [
            {
                "id": "default",
                "name": "Default",
                "description": "Standard animations for all states",
            },
            {
                "id": "friendly",
                "name": "Friendly",
                "description": "Warm, approachable animations",
            },
            {
                "id": "calm",
                "name": "Calm",
                "description": "Gentle, soothing animations for sensitive users",
            },
            {
                "id": "minimal",
                "name": "Minimal",
                "description": "Reduced motion animations",
            },
        ]

    def get_state_animation_info(
        self,
        state: AvatarState,
        animation_set: str = "default",
    ) -> dict:
        """
        Get animation information for a specific state.
        
        Args:
            state: The avatar state
            animation_set: The animation set to use
            
        Returns:
            Animation configuration for the state
        """
        # Animation configurations per state and set
        animations = {
            "default": {
                AvatarState.IDLE: {
                    "animation": "idle_breathe",
                    "duration_ms": 3000,
                    "loop": True,
                },
                AvatarState.LISTENING: {
                    "animation": "listening_nod",
                    "duration_ms": 1500,
                    "loop": True,
                },
                AvatarState.THINKING: {
                    "animation": "thinking_look",
                    "duration_ms": 2000,
                    "loop": True,
                },
                AvatarState.EXPLAINING: {
                    "animation": "explaining_gesture",
                    "duration_ms": 2500,
                    "loop": True,
                },
            },
            "friendly": {
                AvatarState.IDLE: {
                    "animation": "idle_smile",
                    "duration_ms": 3500,
                    "loop": True,
                },
                AvatarState.LISTENING: {
                    "animation": "listening_eager",
                    "duration_ms": 1500,
                    "loop": True,
                },
                AvatarState.THINKING: {
                    "animation": "thinking_curious",
                    "duration_ms": 2000,
                    "loop": True,
                },
                AvatarState.EXPLAINING: {
                    "animation": "explaining_enthusiastic",
                    "duration_ms": 2500,
                    "loop": True,
                },
            },
            "calm": {
                AvatarState.IDLE: {
                    "animation": "idle_gentle",
                    "duration_ms": 4000,
                    "loop": True,
                },
                AvatarState.LISTENING: {
                    "animation": "listening_calm",
                    "duration_ms": 2000,
                    "loop": True,
                },
                AvatarState.THINKING: {
                    "animation": "thinking_peaceful",
                    "duration_ms": 2500,
                    "loop": True,
                },
                AvatarState.EXPLAINING: {
                    "animation": "explaining_gentle",
                    "duration_ms": 3000,
                    "loop": True,
                },
            },
            "minimal": {
                AvatarState.IDLE: {
                    "animation": "idle_static",
                    "duration_ms": 0,
                    "loop": False,
                },
                AvatarState.LISTENING: {
                    "animation": "listening_indicator",
                    "duration_ms": 1000,
                    "loop": True,
                },
                AvatarState.THINKING: {
                    "animation": "thinking_indicator",
                    "duration_ms": 1000,
                    "loop": True,
                },
                AvatarState.EXPLAINING: {
                    "animation": "explaining_indicator",
                    "duration_ms": 1000,
                    "loop": True,
                },
            },
        }
        
        set_animations = animations.get(animation_set, animations["default"])
        return set_animations.get(state, animations["default"][state])
