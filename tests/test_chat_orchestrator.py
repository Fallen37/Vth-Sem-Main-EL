"""Unit tests for ChatOrchestrator service."""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.chat_orchestrator import (
    ChatOrchestrator,
    ChatResponse,
    UserInput,
    ComprehensionOption,
    OutputModeOption,
    ExplanationPart,
    SessionState,
)
from src.models.enums import InputType, ComprehensionLevel, MessageRole
from src.models.learning_profile import OutputMode, ExplanationStyle
from src.services.rag_engine import RAGResponse, Source


@pytest.fixture
def mock_rag_engine():
    """Create a mock RAG engine."""
    engine = MagicMock()
    engine.query.return_value = RAGResponse(
        answer="Photosynthesis is the process by which plants convert sunlight into energy.",
        sources=[
            Source(
                document_id="doc1",
                chunk_index=0,
                content_preview="Plants use sunlight...",
                similarity=0.85,
                subject="Biology",
                chapter="Plant Life",
                topic="Photosynthesis",
            )
        ],
        confidence=0.85,
        suggested_follow_ups=["What is chlorophyll?", "How do plants breathe?"],
        curriculum_mapping={
            "primary_topic": "photosynthesis",
            "primary_chapter": "Plant Life",
        },
    )
    return engine


@pytest.fixture
def chat_orchestrator(mock_rag_engine):
    """Create a ChatOrchestrator with mocked dependencies."""
    orchestrator = ChatOrchestrator(rag_engine=mock_rag_engine)
    return orchestrator


class TestChatOrchestratorCore:
    """Tests for core ChatOrchestrator functionality."""

    def test_get_comprehension_options(self, chat_orchestrator):
        """Test that comprehension options are returned correctly."""
        options = chat_orchestrator.get_comprehension_options()
        
        assert len(options) == 3
        assert all(isinstance(opt, ComprehensionOption) for opt in options)
        
        # Check all three levels are present
        values = [opt.value for opt in options]
        assert ComprehensionLevel.UNDERSTOOD in values
        assert ComprehensionLevel.PARTIAL in values
        assert ComprehensionLevel.NOT_UNDERSTOOD in values

    def test_get_output_mode_options(self, chat_orchestrator):
        """Test that output mode options are returned correctly."""
        options = chat_orchestrator.get_output_mode_options()
        
        assert len(options) >= 4
        assert all(isinstance(opt, OutputModeOption) for opt in options)
        
        # Check expected options are present
        option_ids = [opt.id for opt in options]
        assert "more_examples" in option_ids
        assert "diagram" in option_ids
        assert "simpler_words" in option_ids

    @pytest.mark.asyncio
    async def test_process_message_returns_chat_response(self, chat_orchestrator):
        """Test that process_message returns a valid ChatResponse."""
        user_input = UserInput(
            type=InputType.TEXT,
            content="What is photosynthesis?",
            source=MessageRole.STUDENT,
        )
        session_id = uuid4()
        user_id = uuid4()

        response = await chat_orchestrator.process_message(
            input=user_input,
            session_id=session_id,
            user_id=user_id,
        )

        assert isinstance(response, ChatResponse)
        assert response.message is not None
        assert len(response.message) > 0

    @pytest.mark.asyncio
    async def test_process_message_includes_suggested_responses(self, chat_orchestrator):
        """Test that process_message includes suggested responses for button options."""
        user_input = UserInput(
            type=InputType.TEXT,
            content="Explain photosynthesis",
            source=MessageRole.STUDENT,
        )
        session_id = uuid4()
        user_id = uuid4()

        response = await chat_orchestrator.process_message(
            input=user_input,
            session_id=session_id,
            user_id=user_id,
        )

        # Requirements 5.1, 5.5: Should include suggested responses
        assert len(response.suggested_responses) > 0

    @pytest.mark.asyncio
    async def test_process_message_includes_comprehension_buttons_for_explanations(
        self, chat_orchestrator
    ):
        """Test that explanations include comprehension buttons."""
        user_input = UserInput(
            type=InputType.TEXT,
            content="What is photosynthesis?",
            source=MessageRole.STUDENT,
        )
        session_id = uuid4()
        user_id = uuid4()

        response = await chat_orchestrator.process_message(
            input=user_input,
            session_id=session_id,
            user_id=user_id,
        )

        # Requirements 5.2, 7.1: Should include comprehension buttons for explanations
        if response.is_explanation:
            assert len(response.comprehension_buttons) >= 3

    @pytest.mark.asyncio
    async def test_process_message_includes_output_mode_options_for_explanations(
        self, chat_orchestrator
    ):
        """Test that explanations include output mode options."""
        user_input = UserInput(
            type=InputType.TEXT,
            content="Explain how plants make food",
            source=MessageRole.STUDENT,
        )
        session_id = uuid4()
        user_id = uuid4()

        response = await chat_orchestrator.process_message(
            input=user_input,
            session_id=session_id,
            user_id=user_id,
        )

        # Requirements 4.4: Should include output mode options
        if response.is_explanation:
            assert len(response.output_mode_options) > 0


class TestComprehensionFeedback:
    """Tests for comprehension feedback flow."""

    @pytest.mark.asyncio
    async def test_handle_understood_feedback(self, chat_orchestrator):
        """Test handling of 'understood' feedback."""
        session_id = uuid4()
        user_id = uuid4()

        # First, process a message to set up state
        user_input = UserInput(
            type=InputType.TEXT,
            content="What is photosynthesis?",
            source=MessageRole.STUDENT,
        )
        await chat_orchestrator.process_message(
            input=user_input,
            session_id=session_id,
            user_id=user_id,
        )

        # Then handle feedback
        response = await chat_orchestrator.handle_comprehension_feedback(
            feedback=ComprehensionLevel.UNDERSTOOD,
            session_id=session_id,
            user_id=user_id,
        )

        assert isinstance(response, ChatResponse)
        assert "great" in response.message.lower() or "glad" in response.message.lower()
        assert len(response.breakdown_parts) == 0  # No breakdown needed

    @pytest.mark.asyncio
    async def test_handle_partial_feedback_generates_breakdown(self, chat_orchestrator):
        """Test that partial understanding generates breakdown parts."""
        session_id = uuid4()
        user_id = uuid4()

        # First, process a message to set up state
        user_input = UserInput(
            type=InputType.TEXT,
            content="What is photosynthesis?",
            source=MessageRole.STUDENT,
        )
        await chat_orchestrator.process_message(
            input=user_input,
            session_id=session_id,
            user_id=user_id,
        )

        # Then handle partial feedback
        response = await chat_orchestrator.handle_comprehension_feedback(
            feedback=ComprehensionLevel.PARTIAL,
            session_id=session_id,
            user_id=user_id,
        )

        # Requirements 5.3, 7.2: Should generate breakdown parts
        assert isinstance(response, ChatResponse)
        assert len(response.breakdown_parts) > 0
        assert all(isinstance(part, ExplanationPart) for part in response.breakdown_parts)

    @pytest.mark.asyncio
    async def test_handle_not_understood_generates_detailed_breakdown(self, chat_orchestrator):
        """Test that 'not understood' generates detailed breakdown."""
        session_id = uuid4()
        user_id = uuid4()

        # First, process a message to set up state
        user_input = UserInput(
            type=InputType.TEXT,
            content="What is photosynthesis?",
            source=MessageRole.STUDENT,
        )
        await chat_orchestrator.process_message(
            input=user_input,
            session_id=session_id,
            user_id=user_id,
        )

        # Then handle not understood feedback
        response = await chat_orchestrator.handle_comprehension_feedback(
            feedback=ComprehensionLevel.NOT_UNDERSTOOD,
            session_id=session_id,
            user_id=user_id,
        )

        # Requirements 5.3, 7.2: Should generate breakdown parts
        assert isinstance(response, ChatResponse)
        assert len(response.breakdown_parts) > 0


class TestPartSelection:
    """Tests for part selection handling."""

    @pytest.mark.asyncio
    async def test_handle_part_selection(self, chat_orchestrator):
        """Test handling of part selection."""
        session_id = uuid4()
        user_id = uuid4()

        # Set up state with breakdown parts
        user_input = UserInput(
            type=InputType.TEXT,
            content="What is photosynthesis?",
            source=MessageRole.STUDENT,
        )
        await chat_orchestrator.process_message(
            input=user_input,
            session_id=session_id,
            user_id=user_id,
        )

        # Generate breakdown
        await chat_orchestrator.handle_comprehension_feedback(
            feedback=ComprehensionLevel.PARTIAL,
            session_id=session_id,
            user_id=user_id,
        )

        # Select a part
        response = await chat_orchestrator.handle_part_selection(
            part_id="part_0",
            session_id=session_id,
            user_id=user_id,
        )

        # Requirements 5.4, 7.3: Should provide detailed explanation
        assert isinstance(response, ChatResponse)
        assert response.is_explanation
        assert len(response.comprehension_buttons) >= 3

    @pytest.mark.asyncio
    async def test_handle_invalid_part_selection(self, chat_orchestrator):
        """Test handling of invalid part selection."""
        session_id = uuid4()
        user_id = uuid4()

        # Set up minimal state
        user_input = UserInput(
            type=InputType.TEXT,
            content="What is photosynthesis?",
            source=MessageRole.STUDENT,
        )
        await chat_orchestrator.process_message(
            input=user_input,
            session_id=session_id,
            user_id=user_id,
        )

        # Try to select non-existent part
        response = await chat_orchestrator.handle_part_selection(
            part_id="invalid_part",
            session_id=session_id,
            user_id=user_id,
        )

        assert isinstance(response, ChatResponse)
        assert "couldn't find" in response.message.lower()


class TestOutputModeHandling:
    """Tests for output mode handling."""

    @pytest.mark.asyncio
    async def test_change_output_mode(self, chat_orchestrator):
        """Test changing output mode."""
        session_id = uuid4()
        user_id = uuid4()

        # Initialize session
        user_input = UserInput(
            type=InputType.TEXT,
            content="Hello",
            source=MessageRole.STUDENT,
        )
        await chat_orchestrator.process_message(
            input=user_input,
            session_id=session_id,
            user_id=user_id,
        )

        # Change output mode
        response = await chat_orchestrator.change_output_mode(
            mode_id="simpler_words",
            session_id=session_id,
            user_id=user_id,
        )

        # Requirements 4.5: Should confirm the change
        assert isinstance(response, ChatResponse)
        assert "simpler" in response.message.lower()

        # Verify state was updated
        state = chat_orchestrator._session_states[session_id]
        assert state.current_explanation_style.simplify_language is True

    @pytest.mark.asyncio
    async def test_change_to_audio_mode(self, chat_orchestrator):
        """Test changing to audio output mode."""
        session_id = uuid4()
        user_id = uuid4()

        # Initialize session
        user_input = UserInput(
            type=InputType.TEXT,
            content="Hello",
            source=MessageRole.STUDENT,
        )
        await chat_orchestrator.process_message(
            input=user_input,
            session_id=session_id,
            user_id=user_id,
        )

        # Change to audio mode
        response = await chat_orchestrator.change_output_mode(
            mode_id="audio",
            session_id=session_id,
            user_id=user_id,
        )

        assert isinstance(response, ChatResponse)
        
        # Verify state was updated
        state = chat_orchestrator._session_states[session_id]
        assert state.current_output_mode.audio is True


class TestComplexityAdaptation:
    """Tests for complexity adaptation."""

    @pytest.mark.asyncio
    async def test_complexity_factor_with_no_history(self, chat_orchestrator):
        """Test complexity factor calculation with no history."""
        session_id = uuid4()
        user_id = uuid4()

        state = SessionState(
            session_id=session_id,
            user_id=user_id,
        )

        factor = chat_orchestrator._calculate_complexity_factor(state)
        assert factor == 1.0  # Default factor

    @pytest.mark.asyncio
    async def test_complexity_factor_decreases_with_poor_comprehension(self, chat_orchestrator):
        """Test that complexity factor decreases with poor comprehension."""
        session_id = uuid4()
        user_id = uuid4()

        state = SessionState(
            session_id=session_id,
            user_id=user_id,
            comprehension_history={
                "topic1": [
                    ComprehensionLevel.NOT_UNDERSTOOD,
                    ComprehensionLevel.NOT_UNDERSTOOD,
                    ComprehensionLevel.NOT_UNDERSTOOD,
                ]
            },
        )

        factor = chat_orchestrator._calculate_complexity_factor(state)
        assert factor < 1.0  # Should be lower than default

    @pytest.mark.asyncio
    async def test_complexity_factor_increases_with_good_comprehension(self, chat_orchestrator):
        """Test that complexity factor increases with good comprehension."""
        session_id = uuid4()
        user_id = uuid4()

        state = SessionState(
            session_id=session_id,
            user_id=user_id,
            comprehension_history={
                "topic1": [
                    ComprehensionLevel.UNDERSTOOD,
                    ComprehensionLevel.UNDERSTOOD,
                    ComprehensionLevel.UNDERSTOOD,
                    ComprehensionLevel.UNDERSTOOD,
                    ComprehensionLevel.UNDERSTOOD,
                ]
            },
        )

        factor = chat_orchestrator._calculate_complexity_factor(state)
        assert factor >= 1.0  # Should be at or above default

    def test_get_topic_complexity_level(self, chat_orchestrator):
        """Test getting topic complexity level."""
        session_id = uuid4()
        user_id = uuid4()

        # Test with poor comprehension
        state = SessionState(
            session_id=session_id,
            user_id=user_id,
            comprehension_history={
                "topic1": [
                    ComprehensionLevel.NOT_UNDERSTOOD,
                    ComprehensionLevel.NOT_UNDERSTOOD,
                ]
            },
        )

        level = chat_orchestrator.get_topic_complexity_level(state, "topic1")
        assert level == "simple"

        # Test with good comprehension
        state.comprehension_history["topic2"] = [
            ComprehensionLevel.UNDERSTOOD,
            ComprehensionLevel.UNDERSTOOD,
            ComprehensionLevel.UNDERSTOOD,
            ComprehensionLevel.UNDERSTOOD,
        ]

        level = chat_orchestrator.get_topic_complexity_level(state, "topic2")
        assert level == "advanced"


class TestSessionManagement:
    """Tests for session management."""

    @pytest.mark.asyncio
    async def test_pause_and_resume_session(self, chat_orchestrator):
        """Test pausing and resuming a session."""
        session_id = uuid4()
        user_id = uuid4()

        # Initialize session
        user_input = UserInput(
            type=InputType.TEXT,
            content="Hello",
            source=MessageRole.STUDENT,
        )
        await chat_orchestrator.process_message(
            input=user_input,
            session_id=session_id,
            user_id=user_id,
        )

        # Pause session
        await chat_orchestrator.pause_session(session_id, user_id)
        state = chat_orchestrator._session_states[session_id]
        assert state.is_paused is True

        # Try to process message while paused
        response = await chat_orchestrator.process_message(
            input=user_input,
            session_id=session_id,
            user_id=user_id,
        )
        assert "paused" in response.message.lower()

        # Resume session
        response = await chat_orchestrator.resume_session(session_id, user_id)
        assert "welcome back" in response.message.lower()
        assert state.is_paused is False

    def test_clear_session_state(self, chat_orchestrator):
        """Test clearing session state."""
        session_id = uuid4()
        user_id = uuid4()

        # Add a session state
        chat_orchestrator._session_states[session_id] = SessionState(
            session_id=session_id,
            user_id=user_id,
        )

        # Clear it
        chat_orchestrator.clear_session_state(session_id)
        assert session_id not in chat_orchestrator._session_states
