"""Chat Orchestrator Service - manages conversation flow and response formatting."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.enums import (
    InputType,
    MessageRole,
    ComprehensionLevel,
    InteractionSpeed,
)
from src.models.learning_profile import OutputMode, ExplanationStyle
from src.services.rag_engine import RAGEngine, RAGResponse, QueryContext
from src.services.profile_service import ProfileService, Interaction


class VisualAid(BaseModel):
    """Visual aid component for responses."""

    type: str = Field(description="Type: DIAGRAM, CHART, IMAGE, ANIMATION")
    url: Optional[str] = None
    alt_text: str = ""
    caption: str = ""


class ComprehensionOption(BaseModel):
    """Comprehension feedback button option."""

    id: str
    label: str
    icon: str
    value: ComprehensionLevel


class OutputModeOption(BaseModel):
    """Output mode option for responses."""

    id: str
    label: str
    description: str
    enabled: bool = True


class ExplanationPart(BaseModel):
    """A selectable part of an explanation for breakdown."""

    id: str
    title: str
    summary: str
    full_content: str = ""
    can_expand: bool = True


class UserInput(BaseModel):
    """Input from user (student or guardian)."""

    type: InputType
    content: str
    source: MessageRole = MessageRole.STUDENT
    button_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Response from the chat orchestrator."""

    message: str
    audio_url: Optional[str] = None
    visual_aid: Optional[VisualAid] = None
    comprehension_buttons: list[ComprehensionOption] = Field(default_factory=list)
    output_mode_options: list[OutputModeOption] = Field(default_factory=list)
    suggested_responses: list[str] = Field(default_factory=list)
    breakdown_parts: list[ExplanationPart] = Field(default_factory=list)
    sources: list[dict] = Field(default_factory=list)
    confidence: float = 1.0
    is_explanation: bool = False
    topic_id: Optional[str] = None
    topic_name: Optional[str] = None


class SessionState(BaseModel):
    """State for a chat session."""

    session_id: UUID
    user_id: UUID
    current_output_mode: OutputMode = Field(default_factory=OutputMode)
    current_explanation_style: ExplanationStyle = Field(default_factory=ExplanationStyle)
    last_explanation: Optional[str] = None
    last_breakdown_parts: list[ExplanationPart] = Field(default_factory=list)
    last_topic_id: Optional[str] = None
    last_topic_name: Optional[str] = None
    comprehension_history: dict[str, list[ComprehensionLevel]] = Field(default_factory=dict)
    is_paused: bool = False


@dataclass
class ChatOrchestrator:
    """
    Chat Orchestrator for managing conversation flow.
    
    Handles:
    - Processing user messages through RAG
    - Generating responses with all components
    - Comprehension feedback flow
    - Output mode management
    - Complexity adaptation based on history
    
    Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 7.1, 7.2, 7.3, 7.4, 4.4, 4.5
    """

    db: Optional[AsyncSession] = None
    rag_engine: Optional[RAGEngine] = None
    profile_service: Optional[ProfileService] = None
    
    # Session states (in production, use Redis or similar)
    _session_states: dict[UUID, SessionState] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize services lazily."""
        if self.rag_engine is None:
            self.rag_engine = RAGEngine()

    def _get_profile_service(self) -> ProfileService:
        """Get or create profile service."""
        if self.profile_service is None:
            if self.db is None:
                raise ValueError("Database session required for profile service")
            self.profile_service = ProfileService(self.db)
        return self.profile_service

    async def _get_or_create_session_state(
        self,
        session_id: UUID,
        user_id: UUID,
    ) -> SessionState:
        """Get existing session state or create new one with user preferences."""
        if session_id in self._session_states:
            return self._session_states[session_id]

        # Initialize with user preferences if database is available
        if self.db is not None:
            try:
                profile_service = self._get_profile_service()
                preferences = await profile_service.initialize_session_preferences(user_id)
                state = SessionState(
                    session_id=session_id,
                    user_id=user_id,
                    current_output_mode=preferences["output_mode"],
                    current_explanation_style=preferences["explanation_style"],
                )
            except Exception:
                # Fall back to defaults if profile service fails
                state = SessionState(
                    session_id=session_id,
                    user_id=user_id,
                )
        else:
            # No database, use defaults
            state = SessionState(
                session_id=session_id,
                user_id=user_id,
            )

        self._session_states[session_id] = state
        return state

    def _generate_suggested_responses(
        self,
        rag_response: RAGResponse,
        is_explanation: bool,
    ) -> list[str]:
        """
        Generate suggested response buttons for minimal interaction.
        
        Requirements: 5.1, 5.5 - Provide clickable button options and suggested prompts
        """
        suggestions = []

        # Add follow-ups from RAG if available
        if rag_response.suggested_follow_ups:
            suggestions.extend(rag_response.suggested_follow_ups[:3])

        # Add standard helpful prompts
        if is_explanation:
            suggestions.extend([
                "Can you explain that differently?",
                "Give me an example",
                "What's the most important part?",
            ])
        else:
            suggestions.extend([
                "Tell me more",
                "I have another question",
                "Can you simplify this?",
            ])

        # Limit to 5 suggestions and remove duplicates
        seen = set()
        unique_suggestions = []
        for s in suggestions:
            if s.lower() not in seen:
                seen.add(s.lower())
                unique_suggestions.append(s)
        
        return unique_suggestions[:5]

    def get_comprehension_options(self) -> list[ComprehensionOption]:
        """
        Return standard comprehension feedback options.
        
        Requirements: 5.2, 7.1 - Display comprehension buttons after explanations
        """
        return [
            ComprehensionOption(
                id="understood",
                label="I understood! ✓",
                icon="✓",
                value=ComprehensionLevel.UNDERSTOOD,
            ),
            ComprehensionOption(
                id="partial",
                label="I partially understood",
                icon="~",
                value=ComprehensionLevel.PARTIAL,
            ),
            ComprehensionOption(
                id="not_understood",
                label="I didn't understand",
                icon="?",
                value=ComprehensionLevel.NOT_UNDERSTOOD,
            ),
        ]

    def get_output_mode_options(self) -> list[OutputModeOption]:
        """
        Return available output mode options.
        
        Requirements: 4.4 - Offer output mode options
        """
        return [
            OutputModeOption(
                id="more_examples",
                label="More examples",
                description="Show me examples to understand better",
            ),
            OutputModeOption(
                id="diagram",
                label="Show diagram",
                description="Visual representation of the concept",
            ),
            OutputModeOption(
                id="slower_pace",
                label="Slower pace",
                description="Break it down into smaller steps",
            ),
            OutputModeOption(
                id="simpler_words",
                label="Simpler words",
                description="Explain using easier vocabulary",
            ),
            OutputModeOption(
                id="audio",
                label="Read aloud",
                description="Listen to the explanation",
            ),
        ]


    async def process_message(
        self,
        input: UserInput,
        session_id: UUID,
        user_id: UUID,
        grade: Optional[int] = None,
        syllabus: Optional[str] = None,
    ) -> ChatResponse:
        """
        Process a user message and generate a response.
        
        Routes input through RAG and generates ChatResponse with all components
        including suggested responses for button options.
        
        Requirements: 5.1, 5.5 - Provide clickable button options and suggested prompts
        
        Args:
            input: User input (text, voice, image, or button click)
            session_id: Current session ID
            user_id: User's ID
            grade: Optional grade level for curriculum filtering
            syllabus: Optional syllabus type for curriculum filtering
            
        Returns:
            ChatResponse with message, buttons, and all components
        """
        # Get or create session state
        state = await self._get_or_create_session_state(session_id, user_id)

        # Check if session is paused (calm mode)
        if state.is_paused:
            return ChatResponse(
                message="Your session is paused. Take your time. Click 'Resume' when you're ready to continue.",
                suggested_responses=["Resume learning", "I need more time"],
                is_explanation=False,
            )

        # Build query context
        query_context = QueryContext(
            student_id=user_id,
            grade=grade,
            syllabus=syllabus,
            preferred_explanation_style=state.current_explanation_style.model_dump(),
        )

        # Get complexity adjustment based on comprehension history
        complexity_factor = self._calculate_complexity_factor(state)

        # Query RAG engine
        rag_response = self.rag_engine.query(
            question=input.content,
            context=query_context,
        )

        # Determine if this is an explanation (for comprehension buttons)
        is_explanation = self._is_explanation_response(input.content, rag_response)

        # Extract topic info from curriculum mapping
        topic_id = None
        topic_name = None
        if rag_response.curriculum_mapping:
            topic_id = rag_response.curriculum_mapping.get("primary_topic")
            topic_name = topic_id

        # Apply complexity adaptation to the response
        message = self._adapt_complexity(rag_response.answer, complexity_factor)

        # Store last explanation for potential breakdown
        if is_explanation:
            state.last_explanation = message
            state.last_topic_id = topic_id
            state.last_topic_name = topic_name

        # Generate suggested responses
        suggested_responses = self._generate_suggested_responses(rag_response, is_explanation)

        # Build response
        response = ChatResponse(
            message=message,
            comprehension_buttons=self.get_comprehension_options() if is_explanation else [],
            output_mode_options=self.get_output_mode_options() if is_explanation else [],
            suggested_responses=suggested_responses,
            sources=[s.model_dump() for s in rag_response.sources],
            confidence=rag_response.confidence,
            is_explanation=is_explanation,
            topic_id=topic_id,
            topic_name=topic_name,
        )

        # Record interaction for profile learning
        if self.db:
            try:
                profile_service = self._get_profile_service()
                interaction = Interaction(
                    input_type=input.type,
                    topic_id=topic_id,
                    topic_name=topic_name,
                    output_mode_used=state.current_output_mode,
                )
                await profile_service.record_interaction(user_id, interaction)
            except Exception:
                # Don't fail the response if profile update fails
                pass

        return response

    def _is_explanation_response(
        self,
        question: str,
        rag_response: RAGResponse,
    ) -> bool:
        """Determine if the response is an explanation that needs comprehension check."""
        # Check for explanation-type questions
        explanation_keywords = [
            "what is", "what are", "explain", "how does", "how do",
            "why", "describe", "tell me about", "help me understand",
            "can you explain", "what does", "define",
        ]
        question_lower = question.lower()
        
        for keyword in explanation_keywords:
            if keyword in question_lower:
                return True

        # If we have good confidence and sources, it's likely an explanation
        if rag_response.confidence > 0.5 and len(rag_response.sources) > 0:
            return True

        return False

    def _calculate_complexity_factor(self, state: SessionState) -> float:
        """
        Calculate complexity adjustment factor based on comprehension history.
        
        Requirements: 7.4 - Adjust explanation complexity based on comprehension feedback patterns
        
        Returns:
            Factor between 0.5 (simpler) and 1.5 (more complex)
        """
        if not state.comprehension_history:
            return 1.0

        # Calculate average comprehension across all topics
        total_understood = 0
        total_interactions = 0

        for topic_id, feedbacks in state.comprehension_history.items():
            for feedback in feedbacks[-10:]:  # Consider last 10 interactions per topic
                total_interactions += 1
                if feedback == ComprehensionLevel.UNDERSTOOD:
                    total_understood += 1
                elif feedback == ComprehensionLevel.PARTIAL:
                    total_understood += 0.5

        if total_interactions == 0:
            return 1.0

        comprehension_rate = total_understood / total_interactions

        # Map comprehension rate to complexity factor
        # Low comprehension -> lower complexity (0.5-0.8)
        # High comprehension -> higher complexity (1.0-1.5)
        if comprehension_rate < 0.3:
            return 0.5
        elif comprehension_rate < 0.5:
            return 0.7
        elif comprehension_rate < 0.7:
            return 0.9
        elif comprehension_rate < 0.85:
            return 1.0
        else:
            return 1.2

    def _adapt_complexity(self, message: str, complexity_factor: float) -> str:
        """
        Adapt message complexity based on factor.
        
        In a full implementation, this would use LLM to simplify/elaborate.
        For now, we add guidance prefixes.
        """
        if complexity_factor < 0.7:
            # Add simplification note (in production, would actually simplify)
            return message
        elif complexity_factor > 1.1:
            # Could add more detail (in production, would elaborate)
            return message
        return message


    async def handle_comprehension_feedback(
        self,
        feedback: ComprehensionLevel,
        session_id: UUID,
        user_id: UUID,
    ) -> ChatResponse:
        """
        Process comprehension feedback and generate appropriate response.
        
        Requirements: 5.2, 5.3, 7.1, 7.2 - Handle comprehension feedback and generate breakdowns
        
        Args:
            feedback: The comprehension level feedback
            session_id: Current session ID
            user_id: User's ID
            
        Returns:
            ChatResponse with breakdown parts if needed
        """
        state = await self._get_or_create_session_state(session_id, user_id)

        # Record feedback in session state
        topic_id = state.last_topic_id or "general"
        if topic_id not in state.comprehension_history:
            state.comprehension_history[topic_id] = []
        state.comprehension_history[topic_id].append(feedback)

        # Record interaction for profile learning
        if self.db:
            try:
                profile_service = self._get_profile_service()
                interaction = Interaction(
                    input_type=InputType.BUTTON,
                    topic_id=state.last_topic_id,
                    topic_name=state.last_topic_name,
                    comprehension_feedback=feedback,
                    output_mode_used=state.current_output_mode,
                )
                await profile_service.record_interaction(user_id, interaction)
            except Exception:
                pass

        # Generate response based on feedback
        if feedback == ComprehensionLevel.UNDERSTOOD:
            return ChatResponse(
                message="Great job! 🎉 I'm glad that made sense. What would you like to learn about next?",
                suggested_responses=[
                    "Tell me more about this topic",
                    "I have another question",
                    "Let's move to the next topic",
                ],
                is_explanation=False,
            )

        elif feedback == ComprehensionLevel.PARTIAL:
            # Generate breakdown parts for partial understanding
            breakdown_parts = self._generate_breakdown_parts(state.last_explanation)
            state.last_breakdown_parts = breakdown_parts

            return ChatResponse(
                message="No problem! Let's break this down. Which part would you like me to explain more?",
                breakdown_parts=breakdown_parts,
                suggested_responses=[
                    "Explain the first part",
                    "Start from the beginning",
                    "Give me an example",
                ],
                is_explanation=False,
            )

        else:  # NOT_UNDERSTOOD
            # Generate more detailed breakdown for complete non-understanding
            breakdown_parts = self._generate_breakdown_parts(
                state.last_explanation,
                detailed=True,
            )
            state.last_breakdown_parts = breakdown_parts

            return ChatResponse(
                message="That's okay! Learning takes time. Let me break this into smaller pieces. Click on any part you'd like me to explain:",
                breakdown_parts=breakdown_parts,
                suggested_responses=[
                    "Start with the basics",
                    "Use simpler words",
                    "Show me a picture",
                ],
                is_explanation=False,
            )

    def _generate_breakdown_parts(
        self,
        explanation: Optional[str],
        detailed: bool = False,
    ) -> list[ExplanationPart]:
        """
        Generate breakdown parts from an explanation.
        
        Requirements: 5.3, 7.2 - Break explanation into selectable parts
        """
        if not explanation:
            return []

        # Split explanation into logical parts
        # In production, this would use NLP/LLM for better segmentation
        sentences = explanation.replace('\n\n', '\n').split('\n')
        sentences = [s.strip() for s in sentences if s.strip()]

        if len(sentences) <= 1:
            # Try splitting by periods for single paragraph
            sentences = [s.strip() + '.' for s in explanation.split('.') if s.strip()]

        parts = []
        for i, sentence in enumerate(sentences[:5]):  # Limit to 5 parts
            # Generate a title from the first few words
            words = sentence.split()[:4]
            title = ' '.join(words) + ('...' if len(words) >= 4 else '')

            parts.append(ExplanationPart(
                id=f"part_{i}",
                title=f"Part {i + 1}: {title}",
                summary=sentence[:100] + ('...' if len(sentence) > 100 else ''),
                full_content=sentence,
                can_expand=True,
            ))

        # Add a "basics" part if detailed breakdown requested
        if detailed and parts:
            parts.insert(0, ExplanationPart(
                id="basics",
                title="Start with the basics",
                summary="Let me explain the fundamental concept first",
                full_content="",
                can_expand=True,
            ))

        return parts

    async def handle_part_selection(
        self,
        part_id: str,
        session_id: UUID,
        user_id: UUID,
        grade: Optional[int] = None,
        syllabus: Optional[str] = None,
    ) -> ChatResponse:
        """
        Handle selection of an explanation part for detailed explanation.
        
        Requirements: 5.4, 7.3 - Provide in-depth explanation of selected part
        
        Args:
            part_id: ID of the selected part
            session_id: Current session ID
            user_id: User's ID
            grade: Optional grade level
            syllabus: Optional syllabus type
            
        Returns:
            ChatResponse with detailed explanation of the selected part
        """
        state = await self._get_or_create_session_state(session_id, user_id)

        # Find the selected part
        selected_part = None
        for part in state.last_breakdown_parts:
            if part.id == part_id:
                selected_part = part
                break

        if not selected_part:
            return ChatResponse(
                message="I couldn't find that part. Could you try selecting again?",
                breakdown_parts=state.last_breakdown_parts,
                suggested_responses=["Show me all parts again"],
                is_explanation=False,
            )

        # Handle special "basics" part
        if part_id == "basics":
            # Query RAG for a simpler explanation
            query_context = QueryContext(
                student_id=user_id,
                grade=grade,
                syllabus=syllabus,
                preferred_explanation_style={
                    "simplify_language": True,
                    "step_by_step": True,
                    "use_examples": True,
                },
            )

            topic = state.last_topic_name or "this concept"
            rag_response = self.rag_engine.query(
                question=f"Explain the basics of {topic} in very simple terms for a beginner",
                context=query_context,
            )

            return ChatResponse(
                message=rag_response.answer,
                comprehension_buttons=self.get_comprehension_options(),
                output_mode_options=self.get_output_mode_options(),
                suggested_responses=self._generate_suggested_responses(rag_response, True),
                is_explanation=True,
                topic_id=state.last_topic_id,
                topic_name=state.last_topic_name,
            )

        # Generate detailed explanation for the selected part
        query_context = QueryContext(
            student_id=user_id,
            grade=grade,
            syllabus=syllabus,
            preferred_explanation_style=state.current_explanation_style.model_dump(),
        )

        # Use the part content to generate a more detailed explanation
        rag_response = self.rag_engine.query(
            question=f"Explain in more detail: {selected_part.full_content}",
            context=query_context,
        )

        return ChatResponse(
            message=f"Let me explain '{selected_part.title}' in more detail:\n\n{rag_response.answer}",
            comprehension_buttons=self.get_comprehension_options(),
            output_mode_options=self.get_output_mode_options(),
            suggested_responses=self._generate_suggested_responses(rag_response, True),
            sources=[s.model_dump() for s in rag_response.sources],
            confidence=rag_response.confidence,
            is_explanation=True,
            topic_id=state.last_topic_id,
            topic_name=state.last_topic_name,
        )


    async def change_output_mode(
        self,
        mode_id: str,
        session_id: UUID,
        user_id: UUID,
    ) -> ChatResponse:
        """
        Change the output mode for the session.
        
        Requirements: 4.5 - Allow changing output mode at any time
        
        Args:
            mode_id: ID of the output mode to enable
            session_id: Current session ID
            user_id: User's ID
            
        Returns:
            ChatResponse confirming the change
        """
        state = await self._get_or_create_session_state(session_id, user_id)

        # Update session state based on mode
        mode_messages = {
            "more_examples": "I'll include more examples in my explanations.",
            "diagram": "I'll try to include visual diagrams when helpful.",
            "slower_pace": "I'll break things down into smaller steps.",
            "simpler_words": "I'll use simpler vocabulary.",
            "audio": "I'll provide audio versions of explanations.",
        }

        # Update explanation style based on mode
        if mode_id == "more_examples":
            state.current_explanation_style.use_examples = True
        elif mode_id == "diagram":
            state.current_explanation_style.use_diagrams = True
            state.current_output_mode.visual = True
        elif mode_id == "slower_pace":
            state.current_explanation_style.step_by_step = True
        elif mode_id == "simpler_words":
            state.current_explanation_style.simplify_language = True
        elif mode_id == "audio":
            state.current_output_mode.audio = True

        # Update profile with new preferences
        if self.db:
            try:
                from src.models.learning_profile import LearningProfileUpdate
                profile_service = self._get_profile_service()
                await profile_service.update_profile(
                    user_id,
                    LearningProfileUpdate(
                        preferred_output_mode=state.current_output_mode,
                        preferred_explanation_style=state.current_explanation_style,
                    ),
                )
            except Exception:
                pass

        message = mode_messages.get(mode_id, "Output mode updated.")

        return ChatResponse(
            message=message,
            suggested_responses=[
                "Continue with my question",
                "Explain the last topic again",
            ],
            is_explanation=False,
        )

    def get_topic_complexity_level(
        self,
        state: SessionState,
        topic_id: str,
    ) -> str:
        """
        Get the recommended complexity level for a topic based on history.
        
        Requirements: 7.4 - Adjust complexity based on comprehension patterns
        """
        if topic_id not in state.comprehension_history:
            return "medium"

        feedbacks = state.comprehension_history[topic_id]
        if not feedbacks:
            return "medium"

        # Count recent feedback
        recent = feedbacks[-5:]
        understood = sum(1 for f in recent if f == ComprehensionLevel.UNDERSTOOD)
        not_understood = sum(1 for f in recent if f == ComprehensionLevel.NOT_UNDERSTOOD)

        if not_understood >= 2:
            return "simple"
        elif understood >= 4:
            return "advanced"
        else:
            return "medium"

    async def pause_session(self, session_id: UUID, user_id: UUID) -> None:
        """Pause the session (for calm mode)."""
        state = await self._get_or_create_session_state(session_id, user_id)
        state.is_paused = True

    async def resume_session(self, session_id: UUID, user_id: UUID) -> ChatResponse:
        """Resume a paused session."""
        state = await self._get_or_create_session_state(session_id, user_id)
        state.is_paused = False

        return ChatResponse(
            message="Welcome back! I'm here whenever you're ready. What would you like to learn about?",
            suggested_responses=[
                "Continue where we left off",
                "Start something new",
                "Review what we learned",
            ],
            is_explanation=False,
        )

    def clear_session_state(self, session_id: UUID) -> None:
        """Clear session state when session ends."""
        if session_id in self._session_states:
            del self._session_states[session_id]
