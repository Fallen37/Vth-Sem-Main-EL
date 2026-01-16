"""Property-based tests for MultimodalInputHandler.

Feature: autism-science-tutor, Property 8: Multimodal Input Acceptance
Validates: Requirements 3.1, 3.2, 3.3, 3.4

This test validates that for any valid input (text string, audio blob, or image blob),
the MultimodalInputHandler SHALL process it and return a ProcessedInput with normalizedText.
"""

import base64
import pytest
from hypothesis import given, settings, strategies as st, assume, HealthCheck

from src.services.multimodal_input import (
    MultimodalInputHandler,
    ProcessedInput,
    Intent,
    Entity,
    MockSTTService,
    MockVisionService,
)
from src.models.enums import InputType


# Strategies for generating valid test data

# Strategy for generating text input
text_input_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "Zs", "Po")),
    min_size=1,
    max_size=500,
).filter(lambda x: x.strip())

# Strategy for generating question-like text
# Note: Avoid phrases starting with "help" as they match HELP_REQUEST intent first
question_text_strategy = st.sampled_from([
    "What is photosynthesis?",
    "How does gravity work?",
    "Explain the water cycle",
    "Why do plants need sunlight?",
    "What are the states of matter?",
    "Tell me about electricity",
    "Can you explain evaporation?",
    "What is the solar system?",
    "How do animals breathe?",
    "Describe the process of digestion",
])

# Strategy for generating greeting text
greeting_text_strategy = st.sampled_from([
    "Hello",
    "Hi there",
    "Good morning",
    "Hey",
    "Hi",
])

# Strategy for generating help request text
# Note: Avoid phrases ending with "?" as they match QUESTION intent first
help_request_strategy = st.sampled_from([
    "I need help",
    "Help me please",
    "I don't understand",
    "I'm confused",
    "Help with this topic",
])

# Strategy for generating audio data (simulated as bytes)
audio_data_strategy = st.binary(min_size=100, max_size=10000)

# Strategy for generating image data (simulated as bytes)
image_data_strategy = st.binary(min_size=100, max_size=50000)

# Strategy for generating button IDs
button_id_strategy = st.sampled_from([
    "understood",
    "partial",
    "not_understood",
    "break",
    "help",
    "example",
    "next_topic",
    "clarify",
    "part_1",
    "part_2",
])

# Strategy for generating button labels
button_label_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "Zs")),
    min_size=3,
    max_size=50,
).filter(lambda x: x.strip())

# Strategy for input types
input_type_strategy = st.sampled_from([InputType.TEXT, InputType.VOICE, InputType.IMAGE, InputType.BUTTON])


class TestMultimodalInputAcceptance:
    """
    Property 8: Multimodal Input Acceptance
    
    For any valid input (text string, audio blob, or image blob), the 
    MultimodalInputHandler SHALL process it and return a ProcessedInput 
    with normalizedText.
    
    Validates: Requirements 3.1, 3.2, 3.3, 3.4
    """

    @given(text=text_input_strategy)
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_text_input_returns_processed_input_with_normalized_text(
        self,
        text: str,
    ):
        """
        Feature: autism-science-tutor, Property 8: Multimodal Input Acceptance
        Validates: Requirements 3.1
        
        For any valid text string input, the MultimodalInputHandler SHALL 
        process it and return a ProcessedInput with normalizedText.
        """
        assume(len(text.strip()) >= 1)
        
        handler = MultimodalInputHandler()
        result = handler.process_text_input(text)
        
        # Property: SHALL return a ProcessedInput
        assert isinstance(result, ProcessedInput), (
            "process_text_input SHALL return a ProcessedInput"
        )
        
        # Property: SHALL have normalizedText
        assert result.normalized_text is not None, (
            "ProcessedInput SHALL have normalizedText"
        )
        assert isinstance(result.normalized_text, str), (
            "normalizedText SHALL be a string"
        )
        
        # Property: normalizedText should be non-empty for non-empty input
        if text.strip():
            assert len(result.normalized_text) > 0, (
                "normalizedText SHALL be non-empty for non-empty input"
            )
        
        # Property: original_type should be TEXT
        assert result.original_type == InputType.TEXT, (
            "original_type SHALL be TEXT for text input"
        )
        
        # Property: confidence should be 1.0 for text input
        assert result.confidence == 1.0, (
            "Text input SHALL have confidence of 1.0"
        )

    @given(audio_data=audio_data_strategy)
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_voice_input_returns_processed_input_with_normalized_text(
        self,
        audio_data: bytes,
    ):
        """
        Feature: autism-science-tutor, Property 8: Multimodal Input Acceptance
        Validates: Requirements 3.2
        
        For any valid audio blob input, the MultimodalInputHandler SHALL 
        process it and return a ProcessedInput with normalizedText.
        """
        assume(len(audio_data) >= 100)
        
        handler = MultimodalInputHandler()
        result = handler.process_voice_input(audio_data)
        
        # Property: SHALL return a ProcessedInput
        assert isinstance(result, ProcessedInput), (
            "process_voice_input SHALL return a ProcessedInput"
        )
        
        # Property: SHALL have normalizedText
        assert result.normalized_text is not None, (
            "ProcessedInput SHALL have normalizedText"
        )
        assert isinstance(result.normalized_text, str), (
            "normalizedText SHALL be a string"
        )
        
        # Property: original_type should be VOICE
        assert result.original_type == InputType.VOICE, (
            "original_type SHALL be VOICE for voice input"
        )
        
        # Property: metadata should contain audio info
        assert "audio_size_bytes" in result.metadata, (
            "Voice input metadata SHALL contain audio_size_bytes"
        )
        assert result.metadata["audio_size_bytes"] == len(audio_data), (
            "audio_size_bytes SHALL match input size"
        )

    @given(image_data=image_data_strategy)
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_image_input_returns_processed_input_with_normalized_text(
        self,
        image_data: bytes,
    ):
        """
        Feature: autism-science-tutor, Property 8: Multimodal Input Acceptance
        Validates: Requirements 3.3
        
        For any valid image blob input, the MultimodalInputHandler SHALL 
        process it and return a ProcessedInput with normalizedText.
        """
        assume(len(image_data) >= 100)
        
        handler = MultimodalInputHandler()
        result = handler.process_image_input(image_data)
        
        # Property: SHALL return a ProcessedInput
        assert isinstance(result, ProcessedInput), (
            "process_image_input SHALL return a ProcessedInput"
        )
        
        # Property: SHALL have normalizedText
        assert result.normalized_text is not None, (
            "ProcessedInput SHALL have normalizedText"
        )
        assert isinstance(result.normalized_text, str), (
            "normalizedText SHALL be a string"
        )
        
        # Property: original_type should be IMAGE
        assert result.original_type == InputType.IMAGE, (
            "original_type SHALL be IMAGE for image input"
        )
        
        # Property: metadata should contain image info
        assert "image_size_bytes" in result.metadata, (
            "Image input metadata SHALL contain image_size_bytes"
        )
        assert result.metadata["image_size_bytes"] == len(image_data), (
            "image_size_bytes SHALL match input size"
        )

    @given(
        button_id=button_id_strategy,
        button_label=button_label_strategy,
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_button_click_returns_processed_input_with_normalized_text(
        self,
        button_id: str,
        button_label: str,
    ):
        """
        Feature: autism-science-tutor, Property 8: Multimodal Input Acceptance
        Validates: Requirements 3.4
        
        For any valid button click input, the MultimodalInputHandler SHALL 
        process it and return a ProcessedInput with normalizedText.
        """
        assume(len(button_id.strip()) >= 1)
        assume(len(button_label.strip()) >= 1)
        
        handler = MultimodalInputHandler()
        result = handler.process_button_click(
            button_id=button_id,
            button_label=button_label,
        )
        
        # Property: SHALL return a ProcessedInput
        assert isinstance(result, ProcessedInput), (
            "process_button_click SHALL return a ProcessedInput"
        )
        
        # Property: SHALL have normalizedText
        assert result.normalized_text is not None, (
            "ProcessedInput SHALL have normalizedText"
        )
        assert isinstance(result.normalized_text, str), (
            "normalizedText SHALL be a string"
        )
        assert len(result.normalized_text) > 0, (
            "normalizedText SHALL be non-empty for button click"
        )
        
        # Property: original_type should be BUTTON
        assert result.original_type == InputType.BUTTON, (
            "original_type SHALL be BUTTON for button click"
        )
        
        # Property: confidence should be 1.0 for button click
        assert result.confidence == 1.0, (
            "Button click SHALL have confidence of 1.0"
        )
        
        # Property: metadata should contain button info
        assert "button_id" in result.metadata, (
            "Button click metadata SHALL contain button_id"
        )
        assert result.metadata["button_id"] == button_id, (
            "button_id in metadata SHALL match input"
        )


    @given(
        input_type=input_type_strategy,
        text=text_input_strategy,
        audio_data=audio_data_strategy,
        image_data=image_data_strategy,
        button_id=button_id_strategy,
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_universal_input_processor_returns_processed_input(
        self,
        input_type: InputType,
        text: str,
        audio_data: bytes,
        image_data: bytes,
        button_id: str,
    ):
        """
        Feature: autism-science-tutor, Property 8: Multimodal Input Acceptance
        Validates: Requirements 3.1, 3.2, 3.3, 3.4
        
        For any input type, the universal process_input method SHALL 
        return a ProcessedInput with normalizedText.
        """
        assume(len(text.strip()) >= 1)
        assume(len(audio_data) >= 100)
        assume(len(image_data) >= 100)
        
        handler = MultimodalInputHandler()
        
        # Select appropriate content based on input type
        if input_type == InputType.TEXT:
            content = text
        elif input_type == InputType.VOICE:
            content = audio_data
        elif input_type == InputType.IMAGE:
            content = image_data
        else:  # BUTTON
            content = {"id": button_id, "label": "Test Button"}
        
        result = handler.process_input(input_type, content)
        
        # Property: SHALL return a ProcessedInput
        assert isinstance(result, ProcessedInput), (
            f"process_input SHALL return a ProcessedInput for {input_type}"
        )
        
        # Property: SHALL have normalizedText
        assert result.normalized_text is not None, (
            f"ProcessedInput SHALL have normalizedText for {input_type}"
        )
        assert isinstance(result.normalized_text, str), (
            f"normalizedText SHALL be a string for {input_type}"
        )
        
        # Property: original_type should match input type
        assert result.original_type == input_type, (
            f"original_type SHALL be {input_type}"
        )

    @given(text=question_text_strategy)
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_question_text_detected_as_question_intent(
        self,
        text: str,
    ):
        """
        Feature: autism-science-tutor, Property 8: Multimodal Input Acceptance
        Validates: Requirements 3.1
        
        For any question-like text input, the intent SHALL be detected as QUESTION.
        """
        handler = MultimodalInputHandler()
        result = handler.process_text_input(text)
        
        # Property: Question text SHALL be detected as QUESTION intent
        assert result.intent == Intent.QUESTION, (
            f"Question text '{text}' SHALL be detected as QUESTION intent, got {result.intent}"
        )

    @given(text=greeting_text_strategy)
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_greeting_text_detected_as_greeting_intent(
        self,
        text: str,
    ):
        """
        Feature: autism-science-tutor, Property 8: Multimodal Input Acceptance
        Validates: Requirements 3.1
        
        For any greeting text input, the intent SHALL be detected as GREETING.
        """
        handler = MultimodalInputHandler()
        result = handler.process_text_input(text)
        
        # Property: Greeting text SHALL be detected as GREETING intent
        assert result.intent == Intent.GREETING, (
            f"Greeting text '{text}' SHALL be detected as GREETING intent, got {result.intent}"
        )

    @given(text=help_request_strategy)
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_help_request_detected_as_help_intent(
        self,
        text: str,
    ):
        """
        Feature: autism-science-tutor, Property 8: Multimodal Input Acceptance
        Validates: Requirements 3.1
        
        For any help request text input, the intent SHALL be detected as HELP_REQUEST.
        """
        handler = MultimodalInputHandler()
        result = handler.process_text_input(text)
        
        # Property: Help request text SHALL be detected as HELP_REQUEST intent
        assert result.intent == Intent.HELP_REQUEST, (
            f"Help request text '{text}' SHALL be detected as HELP_REQUEST intent, got {result.intent}"
        )

    @given(
        button_id=st.sampled_from(["understood", "partial", "not_understood"]),
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_comprehension_button_detected_as_comprehension_feedback_intent(
        self,
        button_id: str,
    ):
        """
        Feature: autism-science-tutor, Property 8: Multimodal Input Acceptance
        Validates: Requirements 3.4
        
        For any comprehension feedback button click, the intent SHALL be 
        detected as COMPREHENSION_FEEDBACK.
        """
        handler = MultimodalInputHandler()
        result = handler.process_button_click(button_id=button_id)
        
        # Property: Comprehension button SHALL be detected as COMPREHENSION_FEEDBACK intent
        assert result.intent == Intent.COMPREHENSION_FEEDBACK, (
            f"Comprehension button '{button_id}' SHALL be detected as COMPREHENSION_FEEDBACK intent, got {result.intent}"
        )

    @given(
        text=st.text(
            alphabet=st.characters(whitelist_categories=("L", "N", "Zs")),
            min_size=10,
            max_size=200,
        ).filter(lambda x: x.strip()),
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_text_normalization_removes_excessive_whitespace(
        self,
        text: str,
    ):
        """
        Feature: autism-science-tutor, Property 8: Multimodal Input Acceptance
        Validates: Requirements 3.1
        
        For any text input, the normalizedText SHALL have excessive whitespace removed.
        """
        assume(len(text.strip()) >= 1)
        
        # Add excessive whitespace
        text_with_whitespace = f"  {text}   with   extra   spaces  "
        
        handler = MultimodalInputHandler()
        result = handler.process_text_input(text_with_whitespace)
        
        # Property: normalizedText SHALL not have leading/trailing whitespace
        assert result.normalized_text == result.normalized_text.strip(), (
            "normalizedText SHALL not have leading/trailing whitespace"
        )
        
        # Property: normalizedText SHALL not have multiple consecutive spaces
        assert "  " not in result.normalized_text, (
            "normalizedText SHALL not have multiple consecutive spaces"
        )

    @given(
        grade=st.integers(min_value=5, max_value=10),
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_grade_entity_extraction(
        self,
        grade: int,
    ):
        """
        Feature: autism-science-tutor, Property 8: Multimodal Input Acceptance
        Validates: Requirements 3.1
        
        For any text mentioning a grade (5-10), the grade SHALL be extracted as an entity.
        """
        text = f"I am in grade {grade} and need help with science"
        
        handler = MultimodalInputHandler()
        result = handler.process_text_input(text)
        
        # Property: Grade SHALL be extracted as an entity
        grade_entities = [e for e in result.extracted_entities if e.type == "grade"]
        assert len(grade_entities) > 0, (
            f"Grade {grade} SHALL be extracted as an entity"
        )
        assert grade_entities[0].value == str(grade), (
            f"Extracted grade SHALL be {grade}"
        )

    @given(
        subject=st.sampled_from(["physics", "chemistry", "biology", "mathematics", "science"]),
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_subject_entity_extraction(
        self,
        subject: str,
    ):
        """
        Feature: autism-science-tutor, Property 8: Multimodal Input Acceptance
        Validates: Requirements 3.1
        
        For any text mentioning a subject, the subject SHALL be extracted as an entity.
        """
        text = f"I need help with {subject}"
        
        handler = MultimodalInputHandler()
        result = handler.process_text_input(text)
        
        # Property: Subject SHALL be extracted as an entity
        subject_entities = [e for e in result.extracted_entities if e.type == "subject"]
        assert len(subject_entities) > 0, (
            f"Subject '{subject}' SHALL be extracted as an entity"
        )
        assert subject_entities[0].value.lower() == subject.lower(), (
            f"Extracted subject SHALL be {subject}"
        )

    @given(
        language=st.sampled_from(["en", "hi", "ta", "te", "kn"]),
        audio_data=audio_data_strategy,
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_voice_input_accepts_different_languages(
        self,
        language: str,
        audio_data: bytes,
    ):
        """
        Feature: autism-science-tutor, Property 8: Multimodal Input Acceptance
        Validates: Requirements 3.2
        
        For any valid audio input with language specification, the handler 
        SHALL process it and include language in metadata.
        """
        assume(len(audio_data) >= 100)
        
        handler = MultimodalInputHandler()
        result = handler.process_voice_input(audio_data, language=language)
        
        # Property: SHALL return a ProcessedInput
        assert isinstance(result, ProcessedInput), (
            "process_voice_input SHALL return a ProcessedInput"
        )
        
        # Property: metadata SHALL contain language
        assert "language" in result.metadata, (
            "Voice input metadata SHALL contain language"
        )
        assert result.metadata["language"] == language, (
            f"Language in metadata SHALL be {language}"
        )

    @given(
        use_ocr=st.booleans(),
        image_data=image_data_strategy,
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_image_input_supports_ocr_toggle(
        self,
        use_ocr: bool,
        image_data: bytes,
    ):
        """
        Feature: autism-science-tutor, Property 8: Multimodal Input Acceptance
        Validates: Requirements 3.3
        
        For any image input, the handler SHALL support toggling OCR mode 
        and include the setting in metadata.
        """
        assume(len(image_data) >= 100)
        
        handler = MultimodalInputHandler()
        result = handler.process_image_input(image_data, use_ocr=use_ocr)
        
        # Property: SHALL return a ProcessedInput
        assert isinstance(result, ProcessedInput), (
            "process_image_input SHALL return a ProcessedInput"
        )
        
        # Property: metadata SHALL contain ocr_used flag
        assert "ocr_used" in result.metadata, (
            "Image input metadata SHALL contain ocr_used"
        )
        assert result.metadata["ocr_used"] == use_ocr, (
            f"ocr_used in metadata SHALL be {use_ocr}"
        )

    @given(
        text=text_input_strategy,
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_base64_encoded_voice_input_accepted(
        self,
        text: str,
    ):
        """
        Feature: autism-science-tutor, Property 8: Multimodal Input Acceptance
        Validates: Requirements 3.2, 3.4
        
        For any base64-encoded audio input via process_input, the handler 
        SHALL decode and process it correctly.
        """
        assume(len(text.strip()) >= 1)
        
        # Create some bytes and encode as base64
        audio_bytes = text.encode('utf-8') * 10  # Make it longer
        base64_audio = base64.b64encode(audio_bytes).decode('utf-8')
        
        handler = MultimodalInputHandler()
        result = handler.process_input(InputType.VOICE, base64_audio)
        
        # Property: SHALL return a ProcessedInput
        assert isinstance(result, ProcessedInput), (
            "process_input SHALL return a ProcessedInput for base64 voice"
        )
        
        # Property: original_type should be VOICE
        assert result.original_type == InputType.VOICE, (
            "original_type SHALL be VOICE for voice input"
        )

    @given(
        text=text_input_strategy,
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_base64_encoded_image_input_accepted(
        self,
        text: str,
    ):
        """
        Feature: autism-science-tutor, Property 8: Multimodal Input Acceptance
        Validates: Requirements 3.3, 3.4
        
        For any base64-encoded image input via process_input, the handler 
        SHALL decode and process it correctly.
        """
        assume(len(text.strip()) >= 1)
        
        # Create some bytes and encode as base64
        image_bytes = text.encode('utf-8') * 20  # Make it longer
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        
        handler = MultimodalInputHandler()
        result = handler.process_input(InputType.IMAGE, base64_image)
        
        # Property: SHALL return a ProcessedInput
        assert isinstance(result, ProcessedInput), (
            "process_input SHALL return a ProcessedInput for base64 image"
        )
        
        # Property: original_type should be IMAGE
        assert result.original_type == InputType.IMAGE, (
            "original_type SHALL be IMAGE for image input"
        )

    def test_empty_text_input_handled_gracefully(self):
        """
        Feature: autism-science-tutor, Property 8: Multimodal Input Acceptance
        Validates: Requirements 3.1
        
        For empty text input, the handler SHALL return a ProcessedInput 
        with empty normalizedText (graceful handling).
        """
        handler = MultimodalInputHandler()
        result = handler.process_text_input("")
        
        # Property: SHALL return a ProcessedInput
        assert isinstance(result, ProcessedInput), (
            "process_text_input SHALL return a ProcessedInput for empty input"
        )
        
        # Property: normalizedText should be empty string
        assert result.normalized_text == "", (
            "normalizedText SHALL be empty string for empty input"
        )

    def test_whitespace_only_text_input_handled_gracefully(self):
        """
        Feature: autism-science-tutor, Property 8: Multimodal Input Acceptance
        Validates: Requirements 3.1
        
        For whitespace-only text input, the handler SHALL return a ProcessedInput 
        with empty normalizedText (graceful handling).
        """
        handler = MultimodalInputHandler()
        result = handler.process_text_input("   \t\n   ")
        
        # Property: SHALL return a ProcessedInput
        assert isinstance(result, ProcessedInput), (
            "process_text_input SHALL return a ProcessedInput for whitespace input"
        )
        
        # Property: normalizedText should be empty string
        assert result.normalized_text == "", (
            "normalizedText SHALL be empty string for whitespace-only input"
        )
