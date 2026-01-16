"""Multimodal Input Handler Service - processes different input types.

Handles text, voice, image, and button click inputs, normalizing them
for processing by the chat orchestrator.

Requirements: 3.1, 3.2, 3.3, 3.4
"""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Protocol

from pydantic import BaseModel, Field

from src.models.enums import InputType


class Intent(str, Enum):
    """Detected intent from user input."""
    
    QUESTION = "question"
    GREETING = "greeting"
    HELP_REQUEST = "help_request"
    COMPREHENSION_FEEDBACK = "comprehension_feedback"
    TOPIC_CHANGE = "topic_change"
    CLARIFICATION = "clarification"
    EXAMPLE_REQUEST = "example_request"
    BREAK_REQUEST = "break_request"
    UNKNOWN = "unknown"


class Entity(BaseModel):
    """Extracted entity from user input."""
    
    type: str = Field(description="Entity type (topic, grade, subject, etc.)")
    value: str = Field(description="Entity value")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    start_pos: Optional[int] = None
    end_pos: Optional[int] = None


class ProcessedInput(BaseModel):
    """Result of processing multimodal input.
    
    Contains normalized text and extracted information regardless
    of the original input type (text, voice, image, button).
    """
    
    normalized_text: str = Field(description="Normalized text representation of input")
    original_type: InputType = Field(description="Original input type")
    intent: Optional[Intent] = None
    extracted_entities: list[Entity] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class STTService(Protocol):
    """Protocol for Speech-to-Text service integration."""
    
    def transcribe(self, audio_data: bytes, language: str = "en") -> str:
        """Transcribe audio to text."""
        ...
    
    def transcribe_with_confidence(
        self, audio_data: bytes, language: str = "en"
    ) -> tuple[str, float]:
        """Transcribe audio and return confidence score."""
        ...


class VisionService(Protocol):
    """Protocol for Vision/Image analysis service integration."""
    
    def analyze_image(self, image_data: bytes) -> str:
        """Analyze image and extract text/description."""
        ...
    
    def extract_text_ocr(self, image_data: bytes) -> str:
        """Extract text from image using OCR."""
        ...


class MockSTTService:
    """Mock STT service for testing and development."""
    
    def transcribe(self, audio_data: bytes, language: str = "en") -> str:
        """Return placeholder transcription."""
        # In production, integrate with actual STT service (e.g., Whisper, Google STT)
        return "[Voice input transcription placeholder]"
    
    def transcribe_with_confidence(
        self, audio_data: bytes, language: str = "en"
    ) -> tuple[str, float]:
        """Return placeholder transcription with confidence."""
        return "[Voice input transcription placeholder]", 0.9


class MockVisionService:
    """Mock Vision service for testing and development."""
    
    def analyze_image(self, image_data: bytes) -> str:
        """Return placeholder image analysis."""
        # In production, integrate with actual vision service (e.g., GPT-4V, Google Vision)
        return "[Image analysis placeholder - describe what you see in the image]"
    
    def extract_text_ocr(self, image_data: bytes) -> str:
        """Return placeholder OCR result."""
        return "[OCR text extraction placeholder]"



@dataclass
class MultimodalInputHandler:
    """
    Handler for processing multimodal inputs (text, voice, image, button).
    
    Normalizes all input types to a common ProcessedInput format that can
    be used by the chat orchestrator.
    
    Requirements:
    - 3.1: Accept text input
    - 3.2: Accept voice input and transcribe
    - 3.3: Accept image input (photos of textbook pages, handwritten questions)
    - 3.4: Allow switching between input modes freely
    """
    
    stt_service: Optional[STTService] = None
    vision_service: Optional[VisionService] = None
    
    # Intent detection patterns
    _intent_patterns: dict[Intent, list[str]] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize services and patterns."""
        # Use mock services if none provided
        if self.stt_service is None:
            self.stt_service = MockSTTService()
        if self.vision_service is None:
            self.vision_service = MockVisionService()
        
        # Initialize intent patterns
        self._intent_patterns = {
            Intent.QUESTION: [
                r"^what\s", r"^how\s", r"^why\s", r"^when\s", r"^where\s",
                r"^who\s", r"^which\s", r"^can you explain",
                r"\?$", r"^tell me about", r"^explain", r"^describe",
            ],
            Intent.GREETING: [
                r"^hi\b", r"^hello\b", r"^hey\b", r"^good morning",
                r"^good afternoon", r"^good evening",
            ],
            Intent.HELP_REQUEST: [
                r"^help\b", r"^i need help", r"^can you help",
                r"^i don't understand", r"^i'm confused",
            ],
            Intent.COMPREHENSION_FEEDBACK: [
                r"^i understand", r"^i got it", r"^makes sense",
                r"^i don't get it", r"^still confused",
            ],
            Intent.TOPIC_CHANGE: [
                r"^let's talk about", r"^can we discuss",
                r"^i want to learn about", r"^next topic",
            ],
            Intent.CLARIFICATION: [
                r"^what do you mean", r"^can you clarify",
                r"^i meant", r"^to clarify",
            ],
            Intent.EXAMPLE_REQUEST: [
                r"^give me an example", r"^show me an example",
                r"^for example", r"^can you give an example",
            ],
            Intent.BREAK_REQUEST: [
                r"^i need a break", r"^take a break",
                r"^pause", r"^stop for now",
            ],
        }
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text input by cleaning and standardizing."""
        if not text:
            return ""
        
        # Strip whitespace
        normalized = text.strip()
        
        # Remove excessive whitespace
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Remove control characters but keep newlines
        normalized = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', normalized)
        
        return normalized
    
    def _detect_intent(self, text: str) -> Optional[Intent]:
        """Detect intent from normalized text."""
        if not text:
            return Intent.UNKNOWN
        
        text_lower = text.lower()
        
        for intent, patterns in self._intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    return intent
        
        return Intent.UNKNOWN
    
    def _extract_entities(self, text: str) -> list[Entity]:
        """Extract entities from text (topics, grades, subjects, etc.)."""
        entities = []
        text_lower = text.lower()
        
        # Extract grade mentions
        grade_match = re.search(r'\b(grade|class)\s*(\d+)\b', text_lower)
        if grade_match:
            grade = int(grade_match.group(2))
            if 5 <= grade <= 10:
                entities.append(Entity(
                    type="grade",
                    value=str(grade),
                    start_pos=grade_match.start(),
                    end_pos=grade_match.end(),
                ))
        
        # Extract subject mentions
        subjects = ["physics", "chemistry", "biology", "mathematics", "science"]
        for subject in subjects:
            if subject in text_lower:
                match = re.search(rf'\b{subject}\b', text_lower)
                if match:
                    entities.append(Entity(
                        type="subject",
                        value=subject.capitalize(),
                        start_pos=match.start(),
                        end_pos=match.end(),
                    ))
        
        # Extract chapter/topic mentions
        chapter_match = re.search(
            r'\b(chapter|topic|unit)\s+(\d+|[a-z]+(?:\s+[a-z]+)*)\b',
            text_lower
        )
        if chapter_match:
            entities.append(Entity(
                type="chapter",
                value=chapter_match.group(2),
                start_pos=chapter_match.start(),
                end_pos=chapter_match.end(),
            ))
        
        return entities
    
    def process_text_input(self, text: str) -> ProcessedInput:
        """
        Process text input - normalize and extract intent.
        
        Requirements: 3.1 - Accept text input from the student
        
        Args:
            text: Raw text input from user
            
        Returns:
            ProcessedInput with normalized text and extracted information
        """
        normalized = self._normalize_text(text)
        intent = self._detect_intent(normalized)
        entities = self._extract_entities(normalized)
        
        return ProcessedInput(
            normalized_text=normalized,
            original_type=InputType.TEXT,
            intent=intent,
            extracted_entities=entities,
            confidence=1.0,  # Text input has full confidence
            metadata={"original_length": len(text)},
        )
    
    def process_voice_input(
        self,
        audio_data: bytes,
        language: str = "en",
    ) -> ProcessedInput:
        """
        Process voice input - integrate STT service.
        
        Requirements: 3.2 - Accept voice input and transcribe it for processing
        
        Args:
            audio_data: Raw audio bytes
            language: Language code for transcription
            
        Returns:
            ProcessedInput with transcribed and normalized text
        """
        # Transcribe audio to text
        transcription, confidence = self.stt_service.transcribe_with_confidence(
            audio_data, language
        )
        
        # Normalize the transcription
        normalized = self._normalize_text(transcription)
        intent = self._detect_intent(normalized)
        entities = self._extract_entities(normalized)
        
        return ProcessedInput(
            normalized_text=normalized,
            original_type=InputType.VOICE,
            intent=intent,
            extracted_entities=entities,
            confidence=confidence,
            metadata={
                "language": language,
                "audio_size_bytes": len(audio_data),
            },
        )
    
    def process_image_input(
        self,
        image_data: bytes,
        use_ocr: bool = True,
    ) -> ProcessedInput:
        """
        Process image input - integrate vision service.
        
        Requirements: 3.3 - Accept image input (photos of textbook pages,
        handwritten questions, diagrams)
        
        Args:
            image_data: Raw image bytes
            use_ocr: Whether to use OCR for text extraction
            
        Returns:
            ProcessedInput with extracted text/description
        """
        # Extract text or analyze image
        if use_ocr:
            extracted_text = self.vision_service.extract_text_ocr(image_data)
        else:
            extracted_text = self.vision_service.analyze_image(image_data)
        
        # Normalize the extracted text
        normalized = self._normalize_text(extracted_text)
        intent = self._detect_intent(normalized)
        entities = self._extract_entities(normalized)
        
        return ProcessedInput(
            normalized_text=normalized,
            original_type=InputType.IMAGE,
            intent=intent,
            extracted_entities=entities,
            confidence=0.8,  # Image processing has lower confidence
            metadata={
                "image_size_bytes": len(image_data),
                "ocr_used": use_ocr,
            },
        )
    
    def process_button_click(
        self,
        button_id: str,
        button_label: Optional[str] = None,
        button_value: Optional[str] = None,
    ) -> ProcessedInput:
        """
        Process button click - handle button interactions.
        
        Requirements: 3.4 - Allow switching between input modes freely
        (buttons are a form of input mode)
        
        Args:
            button_id: Unique identifier of the clicked button
            button_label: Human-readable label of the button
            button_value: Value associated with the button
            
        Returns:
            ProcessedInput representing the button action
        """
        # Use button label or value as the normalized text
        normalized = button_label or button_value or button_id
        
        # Detect intent based on button context
        intent = self._detect_button_intent(button_id, button_value)
        
        # Extract any entities from button value
        entities = []
        if button_value:
            entities = self._extract_entities(button_value)
        
        return ProcessedInput(
            normalized_text=normalized,
            original_type=InputType.BUTTON,
            intent=intent,
            extracted_entities=entities,
            confidence=1.0,  # Button clicks have full confidence
            metadata={
                "button_id": button_id,
                "button_label": button_label,
                "button_value": button_value,
            },
        )
    
    def _detect_button_intent(
        self,
        button_id: str,
        button_value: Optional[str],
    ) -> Intent:
        """Detect intent from button click context."""
        button_id_lower = button_id.lower()
        
        # Comprehension feedback buttons
        if any(x in button_id_lower for x in ["understood", "partial", "not_understood"]):
            return Intent.COMPREHENSION_FEEDBACK
        
        # Help/break buttons
        if "break" in button_id_lower or "pause" in button_id_lower:
            return Intent.BREAK_REQUEST
        if "help" in button_id_lower:
            return Intent.HELP_REQUEST
        
        # Example request buttons
        if "example" in button_id_lower:
            return Intent.EXAMPLE_REQUEST
        
        # Topic/navigation buttons
        if any(x in button_id_lower for x in ["topic", "next", "previous"]):
            return Intent.TOPIC_CHANGE
        
        # Clarification buttons
        if any(x in button_id_lower for x in ["clarify", "explain_more", "part_"]):
            return Intent.CLARIFICATION
        
        return Intent.UNKNOWN
    
    def process_input(
        self,
        input_type: InputType,
        content: Any,
        **kwargs,
    ) -> ProcessedInput:
        """
        Universal input processor that routes to appropriate handler.
        
        Requirements: 3.4 - Allow switching between input modes freely
        
        Args:
            input_type: Type of input (TEXT, VOICE, IMAGE, BUTTON)
            content: Input content (str for text, bytes for voice/image, dict for button)
            **kwargs: Additional arguments for specific handlers
            
        Returns:
            ProcessedInput with normalized text and extracted information
        """
        if input_type == InputType.TEXT:
            return self.process_text_input(str(content))
        
        elif input_type == InputType.VOICE:
            if isinstance(content, str):
                # Assume base64 encoded audio
                content = base64.b64decode(content)
            return self.process_voice_input(content, **kwargs)
        
        elif input_type == InputType.IMAGE:
            if isinstance(content, str):
                # Assume base64 encoded image
                content = base64.b64decode(content)
            return self.process_image_input(content, **kwargs)
        
        elif input_type == InputType.BUTTON:
            if isinstance(content, dict):
                return self.process_button_click(
                    button_id=content.get("id", ""),
                    button_label=content.get("label"),
                    button_value=content.get("value"),
                )
            else:
                return self.process_button_click(button_id=str(content))
        
        else:
            # Unknown input type - treat as text
            return self.process_text_input(str(content))
