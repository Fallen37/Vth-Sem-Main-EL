"""Property-based tests for ChatOrchestrator.

Feature: autism-science-tutor, Property 13: Button Options for Minimal Interaction
Validates: Requirements 5.1, 5.5

This test validates that for any ChatResponse that expects user input, 
it SHALL include suggestedResponses as clickable button options.
"""

import pytest
from uuid import uuid4
from unittest.mock import MagicMock

from hypothesis import given, settings, strategies as st, assume, HealthCheck

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
from src.services.rag_engine import RAGEngine, RAGResponse, Source, QueryContext


# Strategies for generating valid test data
input_type_strategy = st.sampled_from([InputType.TEXT, InputType.VOICE, InputType.IMAGE, InputType.BUTTON])
message_role_strategy = st.sampled_from([MessageRole.STUDENT, MessageRole.GUARDIAN])
comprehension_level_strategy = st.sampled_from(list(ComprehensionLevel))

# Strategy for generating question text
question_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "Zs", "Po")),
    min_size=5,
    max_size=200,
).filter(lambda x: x.strip() and any(c.isalnum() for c in x))

# Strategy for generating explanation-type questions
explanation_question_strategy = st.sampled_from([
    "What is photosynthesis?",
    "Explain how plants make food",
    "How does the water cycle work?",
    "Why do leaves change color?",
    "Describe the process of digestion",
    "What are the states of matter?",
    "Tell me about gravity",
    "Help me understand electricity",
    "Can you explain magnetism?",
    "What does evaporation mean?",
])

# Strategy for generating non-explanation questions
non_explanation_question_strategy = st.sampled_from([
    "Hello",
    "Hi there",
    "Thanks",
    "Okay",
    "Got it",
    "Next topic please",
    "I want to learn something new",
])

# Strategy for generating RAG response answers
answer_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "Zs", "Po")),
    min_size=50,
    max_size=500,
).filter(lambda x: x.strip() and len(x.strip()) >= 50)

# Strategy for generating suggested follow-ups
follow_up_strategy = st.lists(
    st.text(
        alphabet=st.characters(whitelist_categories=("L", "N", "Zs", "Po")),
        min_size=10,
        max_size=50,
    ).filter(lambda x: x.strip()),
    min_size=0,
    max_size=3,
)

# Strategy for confidence scores
confidence_strategy = st.floats(min_value=0.0, max_value=1.0, allow_nan=False)


def create_mock_rag_engine(
    answer: str,
    confidence: float,
    suggested_follow_ups: list[str],
) -> MagicMock:
    """Create a mock RAG engine with specified response."""
    engine = MagicMock(spec=RAGEngine)
    engine.query.return_value = RAGResponse(
        answer=answer,
        sources=[
            Source(
                document_id="doc1",
                chunk_index=0,
                content_preview="Test content preview...",
                similarity=confidence,
                subject="Science",
                chapter="Test Chapter",
                topic="Test Topic",
            )
        ],
        confidence=confidence,
        suggested_follow_ups=suggested_follow_ups,
        curriculum_mapping={
            "primary_topic": "test_topic",
            "primary_chapter": "Test Chapter",
        },
    )
    return engine


class TestButtonOptionsForMinimalInteraction:
    """
    Property 13: Button Options for Minimal Interaction
    
    For any ChatResponse that expects user input, it SHALL include 
    suggestedResponses as clickable button options.
    
    Validates: Requirements 5.1, 5.5
    """

    @given(
        question=explanation_question_strategy,
        answer=answer_strategy,
        confidence=confidence_strategy,
        follow_ups=follow_up_strategy,
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_explanation_responses_include_suggested_responses(
        self,
        question: str,
        answer: str,
        confidence: float,
        follow_ups: list[str],
    ):
        """
        Feature: autism-science-tutor, Property 13: Button Options for Minimal Interaction
        Validates: Requirements 5.1, 5.5
        
        For any explanation response from the Tutor_AI, the ChatResponse SHALL 
        include suggestedResponses as clickable button options to minimize required input.
        """
        assume(len(answer.strip()) >= 50)
        
        # Create mock RAG engine with generated response
        mock_rag = create_mock_rag_engine(answer, confidence, follow_ups)
        orchestrator = ChatOrchestrator(rag_engine=mock_rag)
        
        user_input = UserInput(
            type=InputType.TEXT,
            content=question,
            source=MessageRole.STUDENT,
        )
        session_id = uuid4()
        user_id = uuid4()
        
        response = await orchestrator.process_message(
            input=user_input,
            session_id=session_id,
            user_id=user_id,
        )
        
        # Property: ChatResponse SHALL include suggestedResponses
        assert isinstance(response, ChatResponse), "Response should be a ChatResponse"
        assert isinstance(response.suggested_responses, list), (
            "suggested_responses should be a list"
        )
        assert len(response.suggested_responses) > 0, (
            "ChatResponse expecting user input SHALL include suggestedResponses"
        )
        
        # Property: All suggested responses should be non-empty strings
        for suggestion in response.suggested_responses:
            assert isinstance(suggestion, str), "Each suggestion should be a string"
            assert len(suggestion.strip()) > 0, "Suggestions should not be empty"

    @given(
        question=non_explanation_question_strategy,
        answer=answer_strategy,
        confidence=confidence_strategy,
        follow_ups=follow_up_strategy,
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_non_explanation_responses_include_suggested_responses(
        self,
        question: str,
        answer: str,
        confidence: float,
        follow_ups: list[str],
    ):
        """
        Feature: autism-science-tutor, Property 13: Button Options for Minimal Interaction
        Validates: Requirements 5.1, 5.5
        
        For any non-explanation response from the Tutor_AI, the ChatResponse SHALL 
        still include suggestedResponses to provide clickable options.
        """
        assume(len(answer.strip()) >= 50)
        
        # Create mock RAG engine
        mock_rag = create_mock_rag_engine(answer, confidence, follow_ups)
        orchestrator = ChatOrchestrator(rag_engine=mock_rag)
        
        user_input = UserInput(
            type=InputType.TEXT,
            content=question,
            source=MessageRole.STUDENT,
        )
        session_id = uuid4()
        user_id = uuid4()
        
        response = await orchestrator.process_message(
            input=user_input,
            session_id=session_id,
            user_id=user_id,
        )
        
        # Property: ChatResponse SHALL include suggestedResponses
        assert isinstance(response, ChatResponse), "Response should be a ChatResponse"
        assert isinstance(response.suggested_responses, list), (
            "suggested_responses should be a list"
        )
        assert len(response.suggested_responses) > 0, (
            "ChatResponse SHALL include suggestedResponses for minimal interaction"
        )

    @given(
        input_type=input_type_strategy,
        question=question_strategy,
        answer=answer_strategy,
        confidence=confidence_strategy,
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_all_input_types_receive_suggested_responses(
        self,
        input_type: InputType,
        question: str,
        answer: str,
        confidence: float,
    ):
        """
        Feature: autism-science-tutor, Property 13: Button Options for Minimal Interaction
        Validates: Requirements 5.1, 5.5
        
        For any input type (TEXT, VOICE, IMAGE, BUTTON), the ChatResponse SHALL 
        include suggestedResponses to support non-verbal students.
        """
        assume(len(question.strip()) >= 5)
        assume(len(answer.strip()) >= 50)
        
        # Create mock RAG engine
        mock_rag = create_mock_rag_engine(answer, confidence, [])
        orchestrator = ChatOrchestrator(rag_engine=mock_rag)
        
        user_input = UserInput(
            type=input_type,
            content=question,
            source=MessageRole.STUDENT,
        )
        session_id = uuid4()
        user_id = uuid4()
        
        response = await orchestrator.process_message(
            input=user_input,
            session_id=session_id,
            user_id=user_id,
        )
        
        # Property: All input types SHALL receive suggestedResponses
        assert len(response.suggested_responses) > 0, (
            f"ChatResponse for input type {input_type} SHALL include suggestedResponses"
        )

    @given(
        comprehension=comprehension_level_strategy,
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_comprehension_feedback_responses_include_suggested_responses(
        self,
        comprehension: ComprehensionLevel,
    ):
        """
        Feature: autism-science-tutor, Property 13: Button Options for Minimal Interaction
        Validates: Requirements 5.1, 5.5
        
        For any comprehension feedback response, the ChatResponse SHALL include 
        suggestedResponses to guide the student's next action.
        """
        # Create mock RAG engine
        mock_rag = create_mock_rag_engine(
            "Photosynthesis is the process by which plants convert sunlight into energy.",
            0.85,
            ["What is chlorophyll?"],
        )
        orchestrator = ChatOrchestrator(rag_engine=mock_rag)
        
        session_id = uuid4()
        user_id = uuid4()
        
        # First, process a message to set up state
        user_input = UserInput(
            type=InputType.TEXT,
            content="What is photosynthesis?",
            source=MessageRole.STUDENT,
        )
        await orchestrator.process_message(
            input=user_input,
            session_id=session_id,
            user_id=user_id,
        )
        
        # Then handle comprehension feedback
        response = await orchestrator.handle_comprehension_feedback(
            feedback=comprehension,
            session_id=session_id,
            user_id=user_id,
        )
        
        # Property: Comprehension feedback response SHALL include suggestedResponses
        assert isinstance(response, ChatResponse), "Response should be a ChatResponse"
        assert len(response.suggested_responses) > 0, (
            f"Comprehension feedback ({comprehension}) response SHALL include suggestedResponses"
        )

    @given(
        source=message_role_strategy,
        question=explanation_question_strategy,
        answer=answer_strategy,
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_both_student_and_guardian_inputs_receive_suggested_responses(
        self,
        source: MessageRole,
        question: str,
        answer: str,
    ):
        """
        Feature: autism-science-tutor, Property 13: Button Options for Minimal Interaction
        Validates: Requirements 5.1, 5.5
        
        For any input source (STUDENT or GUARDIAN), the ChatResponse SHALL include 
        suggestedResponses to provide clickable options.
        """
        assume(len(answer.strip()) >= 50)
        
        # Create mock RAG engine
        mock_rag = create_mock_rag_engine(answer, 0.8, [])
        orchestrator = ChatOrchestrator(rag_engine=mock_rag)
        
        user_input = UserInput(
            type=InputType.TEXT,
            content=question,
            source=source,
        )
        session_id = uuid4()
        user_id = uuid4()
        
        response = await orchestrator.process_message(
            input=user_input,
            session_id=session_id,
            user_id=user_id,
        )
        
        # Property: Both student and guardian inputs SHALL receive suggestedResponses
        assert len(response.suggested_responses) > 0, (
            f"ChatResponse for source {source} SHALL include suggestedResponses"
        )

    @given(
        answer=answer_strategy,
        follow_ups=st.lists(
            st.text(
                alphabet=st.characters(whitelist_categories=("L", "N", "Zs")),
                min_size=10,
                max_size=50,
            ).filter(lambda x: x.strip()),
            min_size=1,
            max_size=5,
        ),
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_rag_follow_ups_included_in_suggested_responses(
        self,
        answer: str,
        follow_ups: list[str],
    ):
        """
        Feature: autism-science-tutor, Property 13: Button Options for Minimal Interaction
        Validates: Requirements 5.1, 5.5
        
        For any RAG response with suggested follow-ups, those follow-ups SHALL be 
        included in the ChatResponse's suggestedResponses.
        """
        assume(len(answer.strip()) >= 50)
        assume(all(len(f.strip()) > 0 for f in follow_ups))
        
        # Create mock RAG engine with follow-ups
        mock_rag = create_mock_rag_engine(answer, 0.85, follow_ups)
        orchestrator = ChatOrchestrator(rag_engine=mock_rag)
        
        user_input = UserInput(
            type=InputType.TEXT,
            content="What is photosynthesis?",
            source=MessageRole.STUDENT,
        )
        session_id = uuid4()
        user_id = uuid4()
        
        response = await orchestrator.process_message(
            input=user_input,
            session_id=session_id,
            user_id=user_id,
        )
        
        # Property: RAG follow-ups should be included in suggested responses
        suggested_lower = [s.lower() for s in response.suggested_responses]
        for follow_up in follow_ups[:3]:  # Only first 3 are included
            assert follow_up.lower() in suggested_lower, (
                f"RAG follow-up '{follow_up}' should be in suggestedResponses"
            )

    @pytest.mark.asyncio
    async def test_suggested_responses_limited_to_reasonable_count(self):
        """
        Feature: autism-science-tutor, Property 13: Button Options for Minimal Interaction
        Validates: Requirements 5.1, 5.5
        
        The suggestedResponses SHALL be limited to a reasonable count (max 5) 
        to avoid overwhelming non-verbal students.
        """
        # Create mock RAG engine with many follow-ups
        many_follow_ups = [
            "Follow up 1",
            "Follow up 2", 
            "Follow up 3",
            "Follow up 4",
            "Follow up 5",
            "Follow up 6",
            "Follow up 7",
        ]
        mock_rag = create_mock_rag_engine(
            "This is a detailed explanation about science.",
            0.85,
            many_follow_ups,
        )
        orchestrator = ChatOrchestrator(rag_engine=mock_rag)
        
        user_input = UserInput(
            type=InputType.TEXT,
            content="Explain photosynthesis",
            source=MessageRole.STUDENT,
        )
        session_id = uuid4()
        user_id = uuid4()
        
        response = await orchestrator.process_message(
            input=user_input,
            session_id=session_id,
            user_id=user_id,
        )
        
        # Property: suggestedResponses should be limited to avoid overwhelming users
        assert len(response.suggested_responses) <= 5, (
            f"suggestedResponses should be limited to 5, got {len(response.suggested_responses)}"
        )

    @pytest.mark.asyncio
    async def test_paused_session_includes_suggested_responses(self):
        """
        Feature: autism-science-tutor, Property 13: Button Options for Minimal Interaction
        Validates: Requirements 5.1, 5.5
        
        Even when a session is paused (calm mode), the ChatResponse SHALL include 
        suggestedResponses to guide the student.
        """
        mock_rag = create_mock_rag_engine("Test answer", 0.8, [])
        orchestrator = ChatOrchestrator(rag_engine=mock_rag)
        
        session_id = uuid4()
        user_id = uuid4()
        
        # Initialize session
        user_input = UserInput(
            type=InputType.TEXT,
            content="Hello",
            source=MessageRole.STUDENT,
        )
        await orchestrator.process_message(
            input=user_input,
            session_id=session_id,
            user_id=user_id,
        )
        
        # Pause the session
        await orchestrator.pause_session(session_id, user_id)
        
        # Try to send a message while paused
        response = await orchestrator.process_message(
            input=user_input,
            session_id=session_id,
            user_id=user_id,
        )
        
        # Property: Paused session response SHALL include suggestedResponses
        assert len(response.suggested_responses) > 0, (
            "Paused session response SHALL include suggestedResponses"
        )

    @pytest.mark.asyncio
    async def test_resume_session_includes_suggested_responses(self):
        """
        Feature: autism-science-tutor, Property 13: Button Options for Minimal Interaction
        Validates: Requirements 5.1, 5.5
        
        When resuming a session, the ChatResponse SHALL include suggestedResponses 
        to guide the student on what to do next.
        """
        mock_rag = create_mock_rag_engine("Test answer", 0.8, [])
        orchestrator = ChatOrchestrator(rag_engine=mock_rag)
        
        session_id = uuid4()
        user_id = uuid4()
        
        # Initialize and pause session
        user_input = UserInput(
            type=InputType.TEXT,
            content="Hello",
            source=MessageRole.STUDENT,
        )
        await orchestrator.process_message(
            input=user_input,
            session_id=session_id,
            user_id=user_id,
        )
        await orchestrator.pause_session(session_id, user_id)
        
        # Resume session
        response = await orchestrator.resume_session(session_id, user_id)
        
        # Property: Resume response SHALL include suggestedResponses
        assert len(response.suggested_responses) > 0, (
            "Resume session response SHALL include suggestedResponses"
        )

    @given(
        mode_id=st.sampled_from(["more_examples", "diagram", "slower_pace", "simpler_words", "audio"]),
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_output_mode_change_includes_suggested_responses(
        self,
        mode_id: str,
    ):
        """
        Feature: autism-science-tutor, Property 13: Button Options for Minimal Interaction
        Validates: Requirements 5.1, 5.5
        
        When changing output mode, the ChatResponse SHALL include suggestedResponses 
        to guide the student's next action.
        """
        mock_rag = create_mock_rag_engine("Test answer", 0.8, [])
        orchestrator = ChatOrchestrator(rag_engine=mock_rag)
        
        session_id = uuid4()
        user_id = uuid4()
        
        # Initialize session
        user_input = UserInput(
            type=InputType.TEXT,
            content="Hello",
            source=MessageRole.STUDENT,
        )
        await orchestrator.process_message(
            input=user_input,
            session_id=session_id,
            user_id=user_id,
        )
        
        # Change output mode
        response = await orchestrator.change_output_mode(
            mode_id=mode_id,
            session_id=session_id,
            user_id=user_id,
        )
        
        # Property: Output mode change response SHALL include suggestedResponses
        assert len(response.suggested_responses) > 0, (
            f"Output mode change ({mode_id}) response SHALL include suggestedResponses"
        )


class TestComprehensionButtonsAfterExplanations:
    """
    Property 14: Comprehension Buttons After Explanations
    
    For any explanation response from the Tutor_AI, the ChatResponse SHALL include 
    comprehensionButtons with at least three options (Understood, Partially Understood, 
    Not Understood).
    
    Validates: Requirements 5.2, 7.1
    """

    @given(
        question=explanation_question_strategy,
        answer=answer_strategy,
        confidence=st.floats(min_value=0.6, max_value=1.0, allow_nan=False),
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_explanation_responses_include_comprehension_buttons(
        self,
        question: str,
        answer: str,
        confidence: float,
    ):
        """
        Feature: autism-science-tutor, Property 14: Comprehension Buttons After Explanations
        Validates: Requirements 5.2, 7.1
        
        For any explanation response from the Tutor_AI, the ChatResponse SHALL include 
        comprehensionButtons with at least three options.
        """
        assume(len(answer.strip()) >= 50)
        
        # Create mock RAG engine with high confidence (explanation-type response)
        mock_rag = create_mock_rag_engine(answer, confidence, [])
        orchestrator = ChatOrchestrator(rag_engine=mock_rag)
        
        user_input = UserInput(
            type=InputType.TEXT,
            content=question,
            source=MessageRole.STUDENT,
        )
        session_id = uuid4()
        user_id = uuid4()
        
        response = await orchestrator.process_message(
            input=user_input,
            session_id=session_id,
            user_id=user_id,
        )
        
        # Property: Explanation responses SHALL include comprehension buttons
        assert response.is_explanation, (
            f"Response to '{question}' should be marked as explanation"
        )
        assert isinstance(response.comprehension_buttons, list), (
            "comprehension_buttons should be a list"
        )
        assert len(response.comprehension_buttons) >= 3, (
            f"Explanation response SHALL include at least 3 comprehension buttons, got {len(response.comprehension_buttons)}"
        )

    @given(
        question=explanation_question_strategy,
        answer=answer_strategy,
        confidence=st.floats(min_value=0.6, max_value=1.0, allow_nan=False),
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_comprehension_buttons_have_required_values(
        self,
        question: str,
        answer: str,
        confidence: float,
    ):
        """
        Feature: autism-science-tutor, Property 14: Comprehension Buttons After Explanations
        Validates: Requirements 5.2, 7.1
        
        For any explanation response, the comprehension buttons SHALL include options 
        for Understood, Partially Understood, and Not Understood.
        """
        assume(len(answer.strip()) >= 50)
        
        mock_rag = create_mock_rag_engine(answer, confidence, [])
        orchestrator = ChatOrchestrator(rag_engine=mock_rag)
        
        user_input = UserInput(
            type=InputType.TEXT,
            content=question,
            source=MessageRole.STUDENT,
        )
        session_id = uuid4()
        user_id = uuid4()
        
        response = await orchestrator.process_message(
            input=user_input,
            session_id=session_id,
            user_id=user_id,
        )
        
        # Property: Comprehension buttons SHALL include all three required values
        if response.is_explanation:
            button_values = {btn.value for btn in response.comprehension_buttons}
            
            assert ComprehensionLevel.UNDERSTOOD in button_values, (
                "Comprehension buttons SHALL include 'Understood' option"
            )
            assert ComprehensionLevel.PARTIAL in button_values, (
                "Comprehension buttons SHALL include 'Partially Understood' option"
            )
            assert ComprehensionLevel.NOT_UNDERSTOOD in button_values, (
                "Comprehension buttons SHALL include 'Not Understood' option"
            )

    @given(
        question=explanation_question_strategy,
        answer=answer_strategy,
        confidence=st.floats(min_value=0.6, max_value=1.0, allow_nan=False),
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_comprehension_buttons_have_valid_structure(
        self,
        question: str,
        answer: str,
        confidence: float,
    ):
        """
        Feature: autism-science-tutor, Property 14: Comprehension Buttons After Explanations
        Validates: Requirements 5.2, 7.1
        
        For any explanation response, each comprehension button SHALL have a valid 
        structure with id, label, icon, and value fields.
        """
        assume(len(answer.strip()) >= 50)
        
        mock_rag = create_mock_rag_engine(answer, confidence, [])
        orchestrator = ChatOrchestrator(rag_engine=mock_rag)
        
        user_input = UserInput(
            type=InputType.TEXT,
            content=question,
            source=MessageRole.STUDENT,
        )
        session_id = uuid4()
        user_id = uuid4()
        
        response = await orchestrator.process_message(
            input=user_input,
            session_id=session_id,
            user_id=user_id,
        )
        
        # Property: Each comprehension button SHALL have valid structure
        if response.is_explanation:
            for button in response.comprehension_buttons:
                assert isinstance(button, ComprehensionOption), (
                    "Each button should be a ComprehensionOption"
                )
                assert button.id and len(button.id.strip()) > 0, (
                    "Button SHALL have a non-empty id"
                )
                assert button.label and len(button.label.strip()) > 0, (
                    "Button SHALL have a non-empty label"
                )
                assert button.icon and len(button.icon.strip()) > 0, (
                    "Button SHALL have a non-empty icon"
                )
                assert isinstance(button.value, ComprehensionLevel), (
                    "Button value SHALL be a ComprehensionLevel"
                )

    @given(
        input_type=st.sampled_from([InputType.TEXT, InputType.VOICE, InputType.IMAGE]),
        question=explanation_question_strategy,
        answer=answer_strategy,
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_all_input_types_receive_comprehension_buttons_for_explanations(
        self,
        input_type: InputType,
        question: str,
        answer: str,
    ):
        """
        Feature: autism-science-tutor, Property 14: Comprehension Buttons After Explanations
        Validates: Requirements 5.2, 7.1
        
        For any input type (TEXT, VOICE, IMAGE) that results in an explanation, 
        the ChatResponse SHALL include comprehension buttons.
        """
        assume(len(answer.strip()) >= 50)
        
        mock_rag = create_mock_rag_engine(answer, 0.85, [])
        orchestrator = ChatOrchestrator(rag_engine=mock_rag)
        
        user_input = UserInput(
            type=input_type,
            content=question,
            source=MessageRole.STUDENT,
        )
        session_id = uuid4()
        user_id = uuid4()
        
        response = await orchestrator.process_message(
            input=user_input,
            session_id=session_id,
            user_id=user_id,
        )
        
        # Property: All input types SHALL receive comprehension buttons for explanations
        if response.is_explanation:
            assert len(response.comprehension_buttons) >= 3, (
                f"Explanation response for input type {input_type} SHALL include at least 3 comprehension buttons"
            )

    @given(
        source=message_role_strategy,
        question=explanation_question_strategy,
        answer=answer_strategy,
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_both_student_and_guardian_receive_comprehension_buttons(
        self,
        source: MessageRole,
        question: str,
        answer: str,
    ):
        """
        Feature: autism-science-tutor, Property 14: Comprehension Buttons After Explanations
        Validates: Requirements 5.2, 7.1
        
        For any input source (STUDENT or GUARDIAN) that results in an explanation, 
        the ChatResponse SHALL include comprehension buttons.
        """
        assume(len(answer.strip()) >= 50)
        
        mock_rag = create_mock_rag_engine(answer, 0.85, [])
        orchestrator = ChatOrchestrator(rag_engine=mock_rag)
        
        user_input = UserInput(
            type=InputType.TEXT,
            content=question,
            source=source,
        )
        session_id = uuid4()
        user_id = uuid4()
        
        response = await orchestrator.process_message(
            input=user_input,
            session_id=session_id,
            user_id=user_id,
        )
        
        # Property: Both student and guardian inputs SHALL receive comprehension buttons
        if response.is_explanation:
            assert len(response.comprehension_buttons) >= 3, (
                f"Explanation response for source {source} SHALL include at least 3 comprehension buttons"
            )

    @given(
        question=non_explanation_question_strategy,
        answer=answer_strategy,
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_non_explanation_responses_may_omit_comprehension_buttons(
        self,
        question: str,
        answer: str,
    ):
        """
        Feature: autism-science-tutor, Property 14: Comprehension Buttons After Explanations
        Validates: Requirements 5.2, 7.1
        
        For any non-explanation response, the ChatResponse MAY omit comprehension buttons 
        (they are only required for explanations).
        """
        assume(len(answer.strip()) >= 50)
        
        mock_rag = create_mock_rag_engine(answer, 0.3, [])  # Low confidence = not explanation
        orchestrator = ChatOrchestrator(rag_engine=mock_rag)
        
        user_input = UserInput(
            type=InputType.TEXT,
            content=question,
            source=MessageRole.STUDENT,
        )
        session_id = uuid4()
        user_id = uuid4()
        
        response = await orchestrator.process_message(
            input=user_input,
            session_id=session_id,
            user_id=user_id,
        )
        
        # Property: Non-explanation responses MAY have empty comprehension buttons
        # This test verifies the inverse - that comprehension buttons are specifically
        # tied to explanation responses
        if not response.is_explanation:
            # Non-explanations may have empty comprehension buttons
            assert isinstance(response.comprehension_buttons, list), (
                "comprehension_buttons should still be a list (possibly empty)"
            )

    @pytest.mark.asyncio
    async def test_get_comprehension_options_returns_three_options(self):
        """
        Feature: autism-science-tutor, Property 14: Comprehension Buttons After Explanations
        Validates: Requirements 5.2, 7.1
        
        The get_comprehension_options() method SHALL return at least three options.
        """
        mock_rag = create_mock_rag_engine("Test answer", 0.8, [])
        orchestrator = ChatOrchestrator(rag_engine=mock_rag)
        
        options = orchestrator.get_comprehension_options()
        
        assert len(options) >= 3, (
            "get_comprehension_options() SHALL return at least 3 options"
        )
        
        # Verify all required values are present
        values = {opt.value for opt in options}
        assert ComprehensionLevel.UNDERSTOOD in values
        assert ComprehensionLevel.PARTIAL in values
        assert ComprehensionLevel.NOT_UNDERSTOOD in values

    @given(
        question=explanation_question_strategy,
        answer=answer_strategy,
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_comprehension_buttons_consistent_across_sessions(
        self,
        question: str,
        answer: str,
    ):
        """
        Feature: autism-science-tutor, Property 14: Comprehension Buttons After Explanations
        Validates: Requirements 5.2, 7.1
        
        For any explanation response, the comprehension buttons SHALL be consistent 
        across different sessions (same options available).
        """
        assume(len(answer.strip()) >= 50)
        
        mock_rag = create_mock_rag_engine(answer, 0.85, [])
        orchestrator = ChatOrchestrator(rag_engine=mock_rag)
        
        user_input = UserInput(
            type=InputType.TEXT,
            content=question,
            source=MessageRole.STUDENT,
        )
        
        # Process same question in two different sessions
        session_id_1 = uuid4()
        session_id_2 = uuid4()
        user_id = uuid4()
        
        response_1 = await orchestrator.process_message(
            input=user_input,
            session_id=session_id_1,
            user_id=user_id,
        )
        
        response_2 = await orchestrator.process_message(
            input=user_input,
            session_id=session_id_2,
            user_id=user_id,
        )
        
        # Property: Comprehension buttons SHALL be consistent across sessions
        if response_1.is_explanation and response_2.is_explanation:
            values_1 = {btn.value for btn in response_1.comprehension_buttons}
            values_2 = {btn.value for btn in response_2.comprehension_buttons}
            
            assert values_1 == values_2, (
                "Comprehension button values SHALL be consistent across sessions"
            )


class TestBreakdownOnNonUnderstanding:
    """
    Property 15: Breakdown on Non-Understanding
    
    For any comprehension feedback indicating "Partially Understood" or "Not Understood",
    the subsequent ChatResponse SHALL include breakdownParts that segment the explanation
    into selectable components.
    
    Validates: Requirements 5.3, 7.2
    """

    @given(
        explanation=answer_strategy,
        feedback=st.sampled_from([ComprehensionLevel.PARTIAL, ComprehensionLevel.NOT_UNDERSTOOD]),
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_non_understanding_feedback_includes_breakdown_parts(
        self,
        explanation: str,
        feedback: ComprehensionLevel,
    ):
        """
        Feature: autism-science-tutor, Property 15: Breakdown on Non-Understanding
        Validates: Requirements 5.3, 7.2
        
        For any comprehension feedback indicating "Partially Understood" or "Not Understood",
        the subsequent ChatResponse SHALL include breakdownParts.
        """
        assume(len(explanation.strip()) >= 50)
        
        # Create mock RAG engine
        mock_rag = create_mock_rag_engine(explanation, 0.85, [])
        orchestrator = ChatOrchestrator(rag_engine=mock_rag)
        
        session_id = uuid4()
        user_id = uuid4()
        
        # First, process an explanation question to set up state
        user_input = UserInput(
            type=InputType.TEXT,
            content="What is photosynthesis?",
            source=MessageRole.STUDENT,
        )
        await orchestrator.process_message(
            input=user_input,
            session_id=session_id,
            user_id=user_id,
        )
        
        # Then handle non-understanding feedback
        response = await orchestrator.handle_comprehension_feedback(
            feedback=feedback,
            session_id=session_id,
            user_id=user_id,
        )
        
        # Property: Non-understanding feedback SHALL include breakdown_parts
        assert isinstance(response, ChatResponse), "Response should be a ChatResponse"
        assert isinstance(response.breakdown_parts, list), (
            "breakdown_parts should be a list"
        )
        assert len(response.breakdown_parts) > 0, (
            f"Comprehension feedback '{feedback}' SHALL include breakdown_parts to segment the explanation"
        )

    @given(
        explanation=answer_strategy,
        feedback=st.sampled_from([ComprehensionLevel.PARTIAL, ComprehensionLevel.NOT_UNDERSTOOD]),
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_breakdown_parts_have_valid_structure(
        self,
        explanation: str,
        feedback: ComprehensionLevel,
    ):
        """
        Feature: autism-science-tutor, Property 15: Breakdown on Non-Understanding
        Validates: Requirements 5.3, 7.2
        
        For any breakdown part generated, it SHALL have a valid structure with
        id, title, summary, and can_expand fields.
        """
        assume(len(explanation.strip()) >= 50)
        
        mock_rag = create_mock_rag_engine(explanation, 0.85, [])
        orchestrator = ChatOrchestrator(rag_engine=mock_rag)
        
        session_id = uuid4()
        user_id = uuid4()
        
        # Set up state with an explanation
        user_input = UserInput(
            type=InputType.TEXT,
            content="Explain how plants make food",
            source=MessageRole.STUDENT,
        )
        await orchestrator.process_message(
            input=user_input,
            session_id=session_id,
            user_id=user_id,
        )
        
        # Handle non-understanding feedback
        response = await orchestrator.handle_comprehension_feedback(
            feedback=feedback,
            session_id=session_id,
            user_id=user_id,
        )
        
        # Property: Each breakdown part SHALL have valid structure
        for part in response.breakdown_parts:
            assert isinstance(part, ExplanationPart), (
                "Each breakdown part should be an ExplanationPart"
            )
            assert part.id and len(part.id.strip()) > 0, (
                "Breakdown part SHALL have a non-empty id"
            )
            assert part.title and len(part.title.strip()) > 0, (
                "Breakdown part SHALL have a non-empty title"
            )
            assert part.summary and len(part.summary.strip()) > 0, (
                "Breakdown part SHALL have a non-empty summary"
            )
            assert isinstance(part.can_expand, bool), (
                "Breakdown part SHALL have a boolean can_expand field"
            )

    @given(
        explanation=answer_strategy,
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_partial_understanding_includes_breakdown_parts(
        self,
        explanation: str,
    ):
        """
        Feature: autism-science-tutor, Property 15: Breakdown on Non-Understanding
        Validates: Requirements 5.3, 7.2
        
        For any "Partially Understood" feedback, the ChatResponse SHALL include
        breakdownParts to help the student identify which part they struggled with.
        """
        assume(len(explanation.strip()) >= 50)
        
        mock_rag = create_mock_rag_engine(explanation, 0.85, [])
        orchestrator = ChatOrchestrator(rag_engine=mock_rag)
        
        session_id = uuid4()
        user_id = uuid4()
        
        # Set up state
        user_input = UserInput(
            type=InputType.TEXT,
            content="What is the water cycle?",
            source=MessageRole.STUDENT,
        )
        await orchestrator.process_message(
            input=user_input,
            session_id=session_id,
            user_id=user_id,
        )
        
        # Handle partial understanding feedback
        response = await orchestrator.handle_comprehension_feedback(
            feedback=ComprehensionLevel.PARTIAL,
            session_id=session_id,
            user_id=user_id,
        )
        
        # Property: Partial understanding SHALL include breakdown_parts
        assert len(response.breakdown_parts) > 0, (
            "PARTIAL comprehension feedback SHALL include breakdown_parts"
        )

    @given(
        explanation=answer_strategy,
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_not_understood_includes_breakdown_parts(
        self,
        explanation: str,
    ):
        """
        Feature: autism-science-tutor, Property 15: Breakdown on Non-Understanding
        Validates: Requirements 5.3, 7.2
        
        For any "Not Understood" feedback, the ChatResponse SHALL include
        breakdownParts to help the student learn in smaller pieces.
        """
        assume(len(explanation.strip()) >= 50)
        
        mock_rag = create_mock_rag_engine(explanation, 0.85, [])
        orchestrator = ChatOrchestrator(rag_engine=mock_rag)
        
        session_id = uuid4()
        user_id = uuid4()
        
        # Set up state
        user_input = UserInput(
            type=InputType.TEXT,
            content="Explain gravity",
            source=MessageRole.STUDENT,
        )
        await orchestrator.process_message(
            input=user_input,
            session_id=session_id,
            user_id=user_id,
        )
        
        # Handle not understood feedback
        response = await orchestrator.handle_comprehension_feedback(
            feedback=ComprehensionLevel.NOT_UNDERSTOOD,
            session_id=session_id,
            user_id=user_id,
        )
        
        # Property: Not understood SHALL include breakdown_parts
        assert len(response.breakdown_parts) > 0, (
            "NOT_UNDERSTOOD comprehension feedback SHALL include breakdown_parts"
        )

    @given(
        explanation=answer_strategy,
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_understood_feedback_does_not_require_breakdown_parts(
        self,
        explanation: str,
    ):
        """
        Feature: autism-science-tutor, Property 15: Breakdown on Non-Understanding
        Validates: Requirements 5.3, 7.2
        
        For any "Understood" feedback, the ChatResponse MAY omit breakdownParts
        since the student has indicated they understood the explanation.
        """
        assume(len(explanation.strip()) >= 50)
        
        mock_rag = create_mock_rag_engine(explanation, 0.85, [])
        orchestrator = ChatOrchestrator(rag_engine=mock_rag)
        
        session_id = uuid4()
        user_id = uuid4()
        
        # Set up state
        user_input = UserInput(
            type=InputType.TEXT,
            content="What is photosynthesis?",
            source=MessageRole.STUDENT,
        )
        await orchestrator.process_message(
            input=user_input,
            session_id=session_id,
            user_id=user_id,
        )
        
        # Handle understood feedback
        response = await orchestrator.handle_comprehension_feedback(
            feedback=ComprehensionLevel.UNDERSTOOD,
            session_id=session_id,
            user_id=user_id,
        )
        
        # Property: Understood feedback MAY have empty breakdown_parts
        # This verifies the inverse - breakdown is specifically for non-understanding
        assert isinstance(response.breakdown_parts, list), (
            "breakdown_parts should still be a list (possibly empty)"
        )
        # Note: We don't assert it's empty, just that it's a valid list

    @given(
        explanation=answer_strategy,
        feedback=st.sampled_from([ComprehensionLevel.PARTIAL, ComprehensionLevel.NOT_UNDERSTOOD]),
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_breakdown_parts_are_selectable(
        self,
        explanation: str,
        feedback: ComprehensionLevel,
    ):
        """
        Feature: autism-science-tutor, Property 15: Breakdown on Non-Understanding
        Validates: Requirements 5.3, 7.2
        
        For any breakdown part, it SHALL be selectable (can_expand=True) to allow
        the student to request deeper coverage of that specific part.
        """
        assume(len(explanation.strip()) >= 50)
        
        mock_rag = create_mock_rag_engine(explanation, 0.85, [])
        orchestrator = ChatOrchestrator(rag_engine=mock_rag)
        
        session_id = uuid4()
        user_id = uuid4()
        
        # Set up state
        user_input = UserInput(
            type=InputType.TEXT,
            content="Describe the process of digestion",
            source=MessageRole.STUDENT,
        )
        await orchestrator.process_message(
            input=user_input,
            session_id=session_id,
            user_id=user_id,
        )
        
        # Handle non-understanding feedback
        response = await orchestrator.handle_comprehension_feedback(
            feedback=feedback,
            session_id=session_id,
            user_id=user_id,
        )
        
        # Property: Breakdown parts SHALL be selectable
        for part in response.breakdown_parts:
            assert part.can_expand is True, (
                f"Breakdown part '{part.title}' SHALL be selectable (can_expand=True)"
            )

    @given(
        explanation=answer_strategy,
        feedback=st.sampled_from([ComprehensionLevel.PARTIAL, ComprehensionLevel.NOT_UNDERSTOOD]),
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_breakdown_parts_have_unique_ids(
        self,
        explanation: str,
        feedback: ComprehensionLevel,
    ):
        """
        Feature: autism-science-tutor, Property 15: Breakdown on Non-Understanding
        Validates: Requirements 5.3, 7.2
        
        For any set of breakdown parts, each part SHALL have a unique id to allow
        proper selection and tracking.
        """
        assume(len(explanation.strip()) >= 50)
        
        mock_rag = create_mock_rag_engine(explanation, 0.85, [])
        orchestrator = ChatOrchestrator(rag_engine=mock_rag)
        
        session_id = uuid4()
        user_id = uuid4()
        
        # Set up state
        user_input = UserInput(
            type=InputType.TEXT,
            content="What are the states of matter?",
            source=MessageRole.STUDENT,
        )
        await orchestrator.process_message(
            input=user_input,
            session_id=session_id,
            user_id=user_id,
        )
        
        # Handle non-understanding feedback
        response = await orchestrator.handle_comprehension_feedback(
            feedback=feedback,
            session_id=session_id,
            user_id=user_id,
        )
        
        # Property: Breakdown parts SHALL have unique ids
        if len(response.breakdown_parts) > 1:
            ids = [part.id for part in response.breakdown_parts]
            assert len(ids) == len(set(ids)), (
                "Breakdown parts SHALL have unique ids"
            )

    @given(
        explanation=answer_strategy,
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_not_understood_includes_basics_option(
        self,
        explanation: str,
    ):
        """
        Feature: autism-science-tutor, Property 15: Breakdown on Non-Understanding
        Validates: Requirements 5.3, 7.2
        
        For any "Not Understood" feedback, the breakdown parts SHALL include a
        "basics" option to help the student start from fundamental concepts.
        """
        assume(len(explanation.strip()) >= 50)
        
        mock_rag = create_mock_rag_engine(explanation, 0.85, [])
        orchestrator = ChatOrchestrator(rag_engine=mock_rag)
        
        session_id = uuid4()
        user_id = uuid4()
        
        # Set up state
        user_input = UserInput(
            type=InputType.TEXT,
            content="Explain magnetism",
            source=MessageRole.STUDENT,
        )
        await orchestrator.process_message(
            input=user_input,
            session_id=session_id,
            user_id=user_id,
        )
        
        # Handle not understood feedback (detailed=True adds basics option)
        response = await orchestrator.handle_comprehension_feedback(
            feedback=ComprehensionLevel.NOT_UNDERSTOOD,
            session_id=session_id,
            user_id=user_id,
        )
        
        # Property: NOT_UNDERSTOOD SHALL include a "basics" option
        part_ids = [part.id for part in response.breakdown_parts]
        assert "basics" in part_ids, (
            "NOT_UNDERSTOOD feedback SHALL include a 'basics' option in breakdown_parts"
        )

    @given(
        question=explanation_question_strategy,
        explanation=answer_strategy,
        feedback=st.sampled_from([ComprehensionLevel.PARTIAL, ComprehensionLevel.NOT_UNDERSTOOD]),
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_breakdown_parts_stored_in_session_state(
        self,
        question: str,
        explanation: str,
        feedback: ComprehensionLevel,
    ):
        """
        Feature: autism-science-tutor, Property 15: Breakdown on Non-Understanding
        Validates: Requirements 5.3, 7.2
        
        For any non-understanding feedback, the generated breakdown parts SHALL be
        stored in the session state for subsequent part selection handling.
        """
        assume(len(explanation.strip()) >= 50)
        
        mock_rag = create_mock_rag_engine(explanation, 0.85, [])
        orchestrator = ChatOrchestrator(rag_engine=mock_rag)
        
        session_id = uuid4()
        user_id = uuid4()
        
        # Set up state
        user_input = UserInput(
            type=InputType.TEXT,
            content=question,
            source=MessageRole.STUDENT,
        )
        await orchestrator.process_message(
            input=user_input,
            session_id=session_id,
            user_id=user_id,
        )
        
        # Handle non-understanding feedback
        response = await orchestrator.handle_comprehension_feedback(
            feedback=feedback,
            session_id=session_id,
            user_id=user_id,
        )
        
        # Property: Breakdown parts SHALL be stored in session state
        state = orchestrator._session_states.get(session_id)
        assert state is not None, "Session state should exist"
        assert len(state.last_breakdown_parts) > 0, (
            "Breakdown parts SHALL be stored in session state for part selection"
        )
        assert state.last_breakdown_parts == response.breakdown_parts, (
            "Stored breakdown parts SHALL match the response breakdown parts"
        )

    @given(
        explanation=answer_strategy,
        feedback=st.sampled_from([ComprehensionLevel.PARTIAL, ComprehensionLevel.NOT_UNDERSTOOD]),
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_breakdown_response_includes_helpful_message(
        self,
        explanation: str,
        feedback: ComprehensionLevel,
    ):
        """
        Feature: autism-science-tutor, Property 15: Breakdown on Non-Understanding
        Validates: Requirements 5.3, 7.2
        
        For any non-understanding feedback, the ChatResponse SHALL include a helpful
        message guiding the student to select a part for deeper explanation.
        """
        assume(len(explanation.strip()) >= 50)
        
        mock_rag = create_mock_rag_engine(explanation, 0.85, [])
        orchestrator = ChatOrchestrator(rag_engine=mock_rag)
        
        session_id = uuid4()
        user_id = uuid4()
        
        # Set up state
        user_input = UserInput(
            type=InputType.TEXT,
            content="Tell me about electricity",
            source=MessageRole.STUDENT,
        )
        await orchestrator.process_message(
            input=user_input,
            session_id=session_id,
            user_id=user_id,
        )
        
        # Handle non-understanding feedback
        response = await orchestrator.handle_comprehension_feedback(
            feedback=feedback,
            session_id=session_id,
            user_id=user_id,
        )
        
        # Property: Response SHALL include a helpful message
        assert response.message and len(response.message.strip()) > 0, (
            "Non-understanding feedback response SHALL include a helpful message"
        )
        # The message should be encouraging and guide the student
        assert not response.is_explanation, (
            "Breakdown response should not be marked as explanation (it's a navigation response)"
        )


class TestPartSelectionTriggersDetail:
    """
    Property 16: Part Selection Triggers Detail
    
    For any ExplanationPart selected by a student, the Tutor_AI SHALL respond with 
    an in-depth explanation focused specifically on that part.
    
    Validates: Requirements 5.4, 7.3
    """

    @given(
        explanation=answer_strategy,
        feedback=st.sampled_from([ComprehensionLevel.PARTIAL, ComprehensionLevel.NOT_UNDERSTOOD]),
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_part_selection_returns_detailed_explanation(
        self,
        explanation: str,
        feedback: ComprehensionLevel,
    ):
        """
        Feature: autism-science-tutor, Property 16: Part Selection Triggers Detail
        Validates: Requirements 5.4, 7.3
        
        For any ExplanationPart selected by a student, the Tutor_AI SHALL respond 
        with an in-depth explanation focused specifically on that part.
        """
        assume(len(explanation.strip()) >= 50)
        
        # Create mock RAG engine
        mock_rag = create_mock_rag_engine(explanation, 0.85, [])
        orchestrator = ChatOrchestrator(rag_engine=mock_rag)
        
        session_id = uuid4()
        user_id = uuid4()
        
        # Step 1: Process an explanation question to set up state
        user_input = UserInput(
            type=InputType.TEXT,
            content="What is photosynthesis?",
            source=MessageRole.STUDENT,
        )
        await orchestrator.process_message(
            input=user_input,
            session_id=session_id,
            user_id=user_id,
        )
        
        # Step 2: Handle non-understanding feedback to get breakdown parts
        breakdown_response = await orchestrator.handle_comprehension_feedback(
            feedback=feedback,
            session_id=session_id,
            user_id=user_id,
        )
        
        # Ensure we have breakdown parts to select from
        assume(len(breakdown_response.breakdown_parts) > 0)
        
        # Step 3: Select a part (not the "basics" part for this test)
        selectable_parts = [p for p in breakdown_response.breakdown_parts if p.id != "basics"]
        assume(len(selectable_parts) > 0)
        
        selected_part = selectable_parts[0]
        
        # Step 4: Handle part selection
        response = await orchestrator.handle_part_selection(
            part_id=selected_part.id,
            session_id=session_id,
            user_id=user_id,
        )
        
        # Property: Part selection SHALL return a detailed explanation
        assert isinstance(response, ChatResponse), "Response should be a ChatResponse"
        assert response.message and len(response.message.strip()) > 0, (
            "Part selection SHALL return a non-empty message with detailed explanation"
        )
        assert response.is_explanation, (
            "Part selection response SHALL be marked as an explanation"
        )

    @given(
        explanation=answer_strategy,
        feedback=st.sampled_from([ComprehensionLevel.PARTIAL, ComprehensionLevel.NOT_UNDERSTOOD]),
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_part_selection_includes_comprehension_buttons(
        self,
        explanation: str,
        feedback: ComprehensionLevel,
    ):
        """
        Feature: autism-science-tutor, Property 16: Part Selection Triggers Detail
        Validates: Requirements 5.4, 7.3
        
        For any part selection response, the ChatResponse SHALL include comprehension 
        buttons to allow the student to provide feedback on the detailed explanation.
        """
        assume(len(explanation.strip()) >= 50)
        
        mock_rag = create_mock_rag_engine(explanation, 0.85, [])
        orchestrator = ChatOrchestrator(rag_engine=mock_rag)
        
        session_id = uuid4()
        user_id = uuid4()
        
        # Set up state with explanation and breakdown
        user_input = UserInput(
            type=InputType.TEXT,
            content="Explain how plants make food",
            source=MessageRole.STUDENT,
        )
        await orchestrator.process_message(
            input=user_input,
            session_id=session_id,
            user_id=user_id,
        )
        
        breakdown_response = await orchestrator.handle_comprehension_feedback(
            feedback=feedback,
            session_id=session_id,
            user_id=user_id,
        )
        
        assume(len(breakdown_response.breakdown_parts) > 0)
        selectable_parts = [p for p in breakdown_response.breakdown_parts if p.id != "basics"]
        assume(len(selectable_parts) > 0)
        
        selected_part = selectable_parts[0]
        
        # Handle part selection
        response = await orchestrator.handle_part_selection(
            part_id=selected_part.id,
            session_id=session_id,
            user_id=user_id,
        )
        
        # Property: Part selection response SHALL include comprehension buttons
        assert len(response.comprehension_buttons) >= 3, (
            "Part selection response SHALL include at least 3 comprehension buttons"
        )
        
        # Verify all required comprehension levels are present
        button_values = {btn.value for btn in response.comprehension_buttons}
        assert ComprehensionLevel.UNDERSTOOD in button_values, (
            "Comprehension buttons SHALL include 'Understood' option"
        )
        assert ComprehensionLevel.PARTIAL in button_values, (
            "Comprehension buttons SHALL include 'Partially Understood' option"
        )
        assert ComprehensionLevel.NOT_UNDERSTOOD in button_values, (
            "Comprehension buttons SHALL include 'Not Understood' option"
        )

    @given(
        explanation=answer_strategy,
        feedback=st.sampled_from([ComprehensionLevel.PARTIAL, ComprehensionLevel.NOT_UNDERSTOOD]),
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_part_selection_includes_output_mode_options(
        self,
        explanation: str,
        feedback: ComprehensionLevel,
    ):
        """
        Feature: autism-science-tutor, Property 16: Part Selection Triggers Detail
        Validates: Requirements 5.4, 7.3
        
        For any part selection response, the ChatResponse SHALL include output mode 
        options to allow the student to request different formats.
        """
        assume(len(explanation.strip()) >= 50)
        
        mock_rag = create_mock_rag_engine(explanation, 0.85, [])
        orchestrator = ChatOrchestrator(rag_engine=mock_rag)
        
        session_id = uuid4()
        user_id = uuid4()
        
        # Set up state
        user_input = UserInput(
            type=InputType.TEXT,
            content="What is the water cycle?",
            source=MessageRole.STUDENT,
        )
        await orchestrator.process_message(
            input=user_input,
            session_id=session_id,
            user_id=user_id,
        )
        
        breakdown_response = await orchestrator.handle_comprehension_feedback(
            feedback=feedback,
            session_id=session_id,
            user_id=user_id,
        )
        
        assume(len(breakdown_response.breakdown_parts) > 0)
        selectable_parts = [p for p in breakdown_response.breakdown_parts if p.id != "basics"]
        assume(len(selectable_parts) > 0)
        
        selected_part = selectable_parts[0]
        
        # Handle part selection
        response = await orchestrator.handle_part_selection(
            part_id=selected_part.id,
            session_id=session_id,
            user_id=user_id,
        )
        
        # Property: Part selection response SHALL include output mode options
        assert len(response.output_mode_options) > 0, (
            "Part selection response SHALL include output mode options"
        )

    @given(
        explanation=answer_strategy,
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_basics_part_selection_returns_simplified_explanation(
        self,
        explanation: str,
    ):
        """
        Feature: autism-science-tutor, Property 16: Part Selection Triggers Detail
        Validates: Requirements 5.4, 7.3
        
        For any selection of the "basics" part, the Tutor_AI SHALL respond with 
        a simplified explanation of the fundamental concept.
        """
        assume(len(explanation.strip()) >= 50)
        
        mock_rag = create_mock_rag_engine(explanation, 0.85, [])
        orchestrator = ChatOrchestrator(rag_engine=mock_rag)
        
        session_id = uuid4()
        user_id = uuid4()
        
        # Set up state
        user_input = UserInput(
            type=InputType.TEXT,
            content="Explain gravity",
            source=MessageRole.STUDENT,
        )
        await orchestrator.process_message(
            input=user_input,
            session_id=session_id,
            user_id=user_id,
        )
        
        # Handle NOT_UNDERSTOOD feedback (which includes "basics" option)
        breakdown_response = await orchestrator.handle_comprehension_feedback(
            feedback=ComprehensionLevel.NOT_UNDERSTOOD,
            session_id=session_id,
            user_id=user_id,
        )
        
        # Verify basics part exists
        basics_parts = [p for p in breakdown_response.breakdown_parts if p.id == "basics"]
        assume(len(basics_parts) > 0)
        
        # Handle basics part selection
        response = await orchestrator.handle_part_selection(
            part_id="basics",
            session_id=session_id,
            user_id=user_id,
        )
        
        # Property: Basics selection SHALL return a simplified explanation
        assert isinstance(response, ChatResponse), "Response should be a ChatResponse"
        assert response.message and len(response.message.strip()) > 0, (
            "Basics selection SHALL return a non-empty simplified explanation"
        )
        assert response.is_explanation, (
            "Basics selection response SHALL be marked as an explanation"
        )
        assert len(response.comprehension_buttons) >= 3, (
            "Basics selection response SHALL include comprehension buttons"
        )

    @given(
        explanation=answer_strategy,
        feedback=st.sampled_from([ComprehensionLevel.PARTIAL, ComprehensionLevel.NOT_UNDERSTOOD]),
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_part_selection_includes_suggested_responses(
        self,
        explanation: str,
        feedback: ComprehensionLevel,
    ):
        """
        Feature: autism-science-tutor, Property 16: Part Selection Triggers Detail
        Validates: Requirements 5.4, 7.3
        
        For any part selection response, the ChatResponse SHALL include suggested 
        responses to support non-verbal students.
        """
        assume(len(explanation.strip()) >= 50)
        
        mock_rag = create_mock_rag_engine(explanation, 0.85, [])
        orchestrator = ChatOrchestrator(rag_engine=mock_rag)
        
        session_id = uuid4()
        user_id = uuid4()
        
        # Set up state
        user_input = UserInput(
            type=InputType.TEXT,
            content="Describe the process of digestion",
            source=MessageRole.STUDENT,
        )
        await orchestrator.process_message(
            input=user_input,
            session_id=session_id,
            user_id=user_id,
        )
        
        breakdown_response = await orchestrator.handle_comprehension_feedback(
            feedback=feedback,
            session_id=session_id,
            user_id=user_id,
        )
        
        assume(len(breakdown_response.breakdown_parts) > 0)
        selectable_parts = [p for p in breakdown_response.breakdown_parts if p.id != "basics"]
        assume(len(selectable_parts) > 0)
        
        selected_part = selectable_parts[0]
        
        # Handle part selection
        response = await orchestrator.handle_part_selection(
            part_id=selected_part.id,
            session_id=session_id,
            user_id=user_id,
        )
        
        # Property: Part selection response SHALL include suggested responses
        assert len(response.suggested_responses) > 0, (
            "Part selection response SHALL include suggested responses for minimal interaction"
        )

    @given(
        explanation=answer_strategy,
        feedback=st.sampled_from([ComprehensionLevel.PARTIAL, ComprehensionLevel.NOT_UNDERSTOOD]),
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_part_selection_response_references_selected_part(
        self,
        explanation: str,
        feedback: ComprehensionLevel,
    ):
        """
        Feature: autism-science-tutor, Property 16: Part Selection Triggers Detail
        Validates: Requirements 5.4, 7.3
        
        For any part selection, the response message SHALL reference the selected 
        part's title to provide context for the detailed explanation.
        """
        assume(len(explanation.strip()) >= 50)
        
        mock_rag = create_mock_rag_engine(explanation, 0.85, [])
        orchestrator = ChatOrchestrator(rag_engine=mock_rag)
        
        session_id = uuid4()
        user_id = uuid4()
        
        # Set up state
        user_input = UserInput(
            type=InputType.TEXT,
            content="What are the states of matter?",
            source=MessageRole.STUDENT,
        )
        await orchestrator.process_message(
            input=user_input,
            session_id=session_id,
            user_id=user_id,
        )
        
        breakdown_response = await orchestrator.handle_comprehension_feedback(
            feedback=feedback,
            session_id=session_id,
            user_id=user_id,
        )
        
        assume(len(breakdown_response.breakdown_parts) > 0)
        selectable_parts = [p for p in breakdown_response.breakdown_parts if p.id != "basics"]
        assume(len(selectable_parts) > 0)
        
        selected_part = selectable_parts[0]
        
        # Handle part selection
        response = await orchestrator.handle_part_selection(
            part_id=selected_part.id,
            session_id=session_id,
            user_id=user_id,
        )
        
        # Property: Response SHALL reference the selected part's title
        assert selected_part.title in response.message, (
            f"Response message SHALL reference the selected part's title '{selected_part.title}'"
        )

    @given(
        explanation=answer_strategy,
        feedback=st.sampled_from([ComprehensionLevel.PARTIAL, ComprehensionLevel.NOT_UNDERSTOOD]),
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_invalid_part_selection_returns_helpful_response(
        self,
        explanation: str,
        feedback: ComprehensionLevel,
    ):
        """
        Feature: autism-science-tutor, Property 16: Part Selection Triggers Detail
        Validates: Requirements 5.4, 7.3
        
        For any invalid part selection (non-existent part_id), the Tutor_AI SHALL 
        return a helpful response with the available breakdown parts.
        """
        assume(len(explanation.strip()) >= 50)
        
        mock_rag = create_mock_rag_engine(explanation, 0.85, [])
        orchestrator = ChatOrchestrator(rag_engine=mock_rag)
        
        session_id = uuid4()
        user_id = uuid4()
        
        # Set up state
        user_input = UserInput(
            type=InputType.TEXT,
            content="Tell me about electricity",
            source=MessageRole.STUDENT,
        )
        await orchestrator.process_message(
            input=user_input,
            session_id=session_id,
            user_id=user_id,
        )
        
        breakdown_response = await orchestrator.handle_comprehension_feedback(
            feedback=feedback,
            session_id=session_id,
            user_id=user_id,
        )
        
        assume(len(breakdown_response.breakdown_parts) > 0)
        
        # Handle invalid part selection
        response = await orchestrator.handle_part_selection(
            part_id="invalid_part_id_that_does_not_exist",
            session_id=session_id,
            user_id=user_id,
        )
        
        # Property: Invalid selection SHALL return helpful response with breakdown parts
        assert isinstance(response, ChatResponse), "Response should be a ChatResponse"
        assert response.message and len(response.message.strip()) > 0, (
            "Invalid part selection SHALL return a helpful message"
        )
        assert len(response.breakdown_parts) > 0, (
            "Invalid part selection SHALL include the available breakdown parts"
        )

    @given(
        explanation=answer_strategy,
        feedback=st.sampled_from([ComprehensionLevel.PARTIAL, ComprehensionLevel.NOT_UNDERSTOOD]),
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_part_selection_preserves_topic_context(
        self,
        explanation: str,
        feedback: ComprehensionLevel,
    ):
        """
        Feature: autism-science-tutor, Property 16: Part Selection Triggers Detail
        Validates: Requirements 5.4, 7.3
        
        For any part selection, the response SHALL preserve the topic context 
        (topic_id and topic_name) from the original explanation.
        """
        assume(len(explanation.strip()) >= 50)
        
        mock_rag = create_mock_rag_engine(explanation, 0.85, [])
        orchestrator = ChatOrchestrator(rag_engine=mock_rag)
        
        session_id = uuid4()
        user_id = uuid4()
        
        # Set up state
        user_input = UserInput(
            type=InputType.TEXT,
            content="Explain magnetism",
            source=MessageRole.STUDENT,
        )
        initial_response = await orchestrator.process_message(
            input=user_input,
            session_id=session_id,
            user_id=user_id,
        )
        
        breakdown_response = await orchestrator.handle_comprehension_feedback(
            feedback=feedback,
            session_id=session_id,
            user_id=user_id,
        )
        
        assume(len(breakdown_response.breakdown_parts) > 0)
        selectable_parts = [p for p in breakdown_response.breakdown_parts if p.id != "basics"]
        assume(len(selectable_parts) > 0)
        
        selected_part = selectable_parts[0]
        
        # Handle part selection
        response = await orchestrator.handle_part_selection(
            part_id=selected_part.id,
            session_id=session_id,
            user_id=user_id,
        )
        
        # Property: Part selection SHALL preserve topic context
        assert response.topic_id == initial_response.topic_id, (
            "Part selection response SHALL preserve the original topic_id"
        )
        assert response.topic_name == initial_response.topic_name, (
            "Part selection response SHALL preserve the original topic_name"
        )

    @given(
        explanation=answer_strategy,
        feedback=st.sampled_from([ComprehensionLevel.PARTIAL, ComprehensionLevel.NOT_UNDERSTOOD]),
        part_index=st.integers(min_value=0, max_value=4),
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_any_selectable_part_triggers_detailed_response(
        self,
        explanation: str,
        feedback: ComprehensionLevel,
        part_index: int,
    ):
        """
        Feature: autism-science-tutor, Property 16: Part Selection Triggers Detail
        Validates: Requirements 5.4, 7.3
        
        For any selectable ExplanationPart (at any index), the Tutor_AI SHALL 
        respond with an in-depth explanation.
        """
        assume(len(explanation.strip()) >= 50)
        
        mock_rag = create_mock_rag_engine(explanation, 0.85, [])
        orchestrator = ChatOrchestrator(rag_engine=mock_rag)
        
        session_id = uuid4()
        user_id = uuid4()
        
        # Set up state
        user_input = UserInput(
            type=InputType.TEXT,
            content="What does evaporation mean?",
            source=MessageRole.STUDENT,
        )
        await orchestrator.process_message(
            input=user_input,
            session_id=session_id,
            user_id=user_id,
        )
        
        breakdown_response = await orchestrator.handle_comprehension_feedback(
            feedback=feedback,
            session_id=session_id,
            user_id=user_id,
        )
        
        # Filter to selectable parts (excluding basics for this test)
        selectable_parts = [p for p in breakdown_response.breakdown_parts if p.id != "basics"]
        assume(len(selectable_parts) > 0)
        
        # Select a part at the given index (modulo to stay in bounds)
        actual_index = part_index % len(selectable_parts)
        selected_part = selectable_parts[actual_index]
        
        # Handle part selection
        response = await orchestrator.handle_part_selection(
            part_id=selected_part.id,
            session_id=session_id,
            user_id=user_id,
        )
        
        # Property: Any selectable part SHALL trigger a detailed response
        assert response.is_explanation, (
            f"Selection of part at index {actual_index} SHALL trigger an explanation response"
        )
        assert response.message and len(response.message.strip()) > 0, (
            f"Selection of part at index {actual_index} SHALL return a non-empty detailed explanation"
        )
        assert len(response.comprehension_buttons) >= 3, (
            f"Selection of part at index {actual_index} SHALL include comprehension buttons"
        )
