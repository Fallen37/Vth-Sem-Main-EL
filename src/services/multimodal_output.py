"""Multimodal Output Renderer Service - generates different output formats.

Handles text, audio, visual aids, and comprehension button rendering
for the chat orchestrator responses.

Requirements: 4.1, 4.2, 4.3
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Protocol

from pydantic import BaseModel, Field


class TextStyle(BaseModel):
    """Style configuration for text rendering."""
    
    font_size: str = Field(default="medium", description="Font size: small, medium, large")
    bold: bool = False
    italic: bool = False
    color: Optional[str] = None
    highlight: bool = False
    simplify_language: bool = False


class VoiceConfig(BaseModel):
    """Configuration for voice/audio generation."""
    
    voice_id: str = Field(default="default", description="Voice identifier")
    speed: float = Field(default=1.0, ge=0.5, le=2.0, description="Speech speed multiplier")
    pitch: float = Field(default=1.0, ge=0.5, le=2.0, description="Voice pitch multiplier")
    language: str = Field(default="en", description="Language code")
    emphasis: bool = Field(default=False, description="Add emphasis to key terms")


class VisualType(str, Enum):
    """Types of visual aids."""
    
    DIAGRAM = "diagram"
    CHART = "chart"
    IMAGE = "image"
    ANIMATION = "animation"
    FLOWCHART = "flowchart"
    ILLUSTRATION = "illustration"


class VisualData(BaseModel):
    """Data for generating visual aids."""
    
    topic: str = Field(description="Topic for the visual")
    description: str = Field(default="", description="Description of what to visualize")
    keywords: list[str] = Field(default_factory=list, description="Keywords for image search")
    data_points: Optional[dict[str, Any]] = None  # For charts
    steps: Optional[list[str]] = None  # For flowcharts


class RenderedText(BaseModel):
    """Result of text rendering."""
    
    content: str = Field(description="The rendered text content")
    html: Optional[str] = None  # HTML formatted version
    markdown: Optional[str] = None  # Markdown formatted version
    style_applied: TextStyle = Field(default_factory=TextStyle)
    word_count: int = 0
    reading_time_seconds: int = 0


class VisualAid(BaseModel):
    """Visual aid component for responses."""
    
    type: VisualType = Field(description="Type of visual aid")
    url: Optional[str] = None
    alt_text: str = ""
    caption: str = ""
    data: Optional[dict[str, Any]] = None  # For dynamic rendering


class ComprehensionOption(BaseModel):
    """Comprehension feedback button option."""
    
    id: str
    label: str
    icon: str
    value: str


class ButtonGroup(BaseModel):
    """Group of buttons for user interaction."""
    
    buttons: list[ComprehensionOption] = Field(default_factory=list)
    layout: str = Field(default="horizontal", description="horizontal or vertical")
    spacing: str = Field(default="medium", description="small, medium, large")


class TTSService(Protocol):
    """Protocol for Text-to-Speech service integration."""
    
    def synthesize(self, text: str, config: VoiceConfig) -> bytes:
        """Synthesize text to audio bytes."""
        ...
    
    def synthesize_to_url(self, text: str, config: VoiceConfig) -> str:
        """Synthesize text and return URL to audio file."""
        ...
    
    def get_available_voices(self) -> list[dict[str, str]]:
        """Get list of available voices."""
        ...


class ImageService(Protocol):
    """Protocol for image/diagram generation service."""
    
    def generate_diagram(self, topic: str, description: str) -> str:
        """Generate a diagram and return URL."""
        ...
    
    def search_image(self, keywords: list[str]) -> str:
        """Search for relevant image and return URL."""
        ...
    
    def generate_chart(self, data: dict[str, Any], chart_type: str) -> str:
        """Generate a chart from data and return URL."""
        ...


class MockTTSService:
    """Mock TTS service for testing and development."""
    
    def synthesize(self, text: str, config: VoiceConfig) -> bytes:
        """Return placeholder audio bytes."""
        # In production, integrate with actual TTS service (e.g., Google TTS, Amazon Polly)
        return b"[Audio placeholder for: " + text[:50].encode() + b"...]"
    
    def synthesize_to_url(self, text: str, config: VoiceConfig) -> str:
        """Return placeholder audio URL."""
        # In production, would upload to storage and return URL
        return f"/api/audio/placeholder?text={text[:20]}&voice={config.voice_id}"
    
    def get_available_voices(self) -> list[dict[str, str]]:
        """Return list of mock voices."""
        return [
            {"id": "default", "name": "Default Voice", "language": "en"},
            {"id": "child_friendly", "name": "Child Friendly", "language": "en"},
            {"id": "slow_clear", "name": "Slow and Clear", "language": "en"},
            {"id": "hindi", "name": "Hindi Voice", "language": "hi"},
        ]


class MockImageService:
    """Mock image service for testing and development."""
    
    def generate_diagram(self, topic: str, description: str) -> str:
        """Return placeholder diagram URL."""
        # In production, integrate with diagram generation service
        return f"/api/diagrams/placeholder?topic={topic}"
    
    def search_image(self, keywords: list[str]) -> str:
        """Return placeholder image URL."""
        # In production, integrate with image search API
        keyword_str = "_".join(keywords[:3])
        return f"/api/images/placeholder?keywords={keyword_str}"
    
    def generate_chart(self, data: dict[str, Any], chart_type: str) -> str:
        """Return placeholder chart URL."""
        # In production, integrate with charting library
        return f"/api/charts/placeholder?type={chart_type}"


@dataclass
class MultimodalOutputRenderer:
    """
    Renderer for generating multimodal output formats.
    
    Handles:
    - Text formatting with styles
    - Audio generation via TTS
    - Visual aid generation/retrieval
    - Comprehension button rendering
    
    Requirements:
    - 4.1: Provide text-based explanations
    - 4.2: Provide voice/audio explanations
    - 4.3: Generate or retrieve relevant diagrams and visual aids
    """
    
    tts_service: Optional[TTSService] = None
    image_service: Optional[ImageService] = None
    
    # Default configurations
    default_text_style: TextStyle = field(default_factory=TextStyle)
    default_voice_config: VoiceConfig = field(default_factory=VoiceConfig)
    
    def __post_init__(self):
        """Initialize services with mocks if not provided."""
        if self.tts_service is None:
            self.tts_service = MockTTSService()
        if self.image_service is None:
            self.image_service = MockImageService()
    
    def render_text(
        self,
        content: str,
        style: Optional[TextStyle] = None,
    ) -> RenderedText:
        """
        Format text with the specified style.
        
        Requirements: 4.1 - Provide text-based explanations
        
        Args:
            content: The text content to render
            style: Optional style configuration
            
        Returns:
            RenderedText with formatted content
        """
        if not content:
            return RenderedText(
                content="",
                style_applied=style or self.default_text_style,
                word_count=0,
                reading_time_seconds=0,
            )
        
        style = style or self.default_text_style
        
        # Apply text transformations based on style
        rendered_content = content
        
        # Simplify language if requested
        if style.simplify_language:
            rendered_content = self._simplify_text(rendered_content)
        
        # Calculate metrics
        word_count = len(rendered_content.split())
        # Average reading speed: 200 words per minute for children
        reading_time_seconds = max(1, (word_count * 60) // 200)
        
        # Generate HTML version
        html_content = self._to_html(rendered_content, style)
        
        # Generate Markdown version
        markdown_content = self._to_markdown(rendered_content, style)
        
        return RenderedText(
            content=rendered_content,
            html=html_content,
            markdown=markdown_content,
            style_applied=style,
            word_count=word_count,
            reading_time_seconds=reading_time_seconds,
        )
    
    def _simplify_text(self, text: str) -> str:
        """
        Simplify text for easier comprehension.
        
        In production, this would use NLP/LLM for actual simplification.
        """
        # Basic simplification: break long sentences
        # In production, integrate with LLM for proper simplification
        return text
    
    def _to_html(self, content: str, style: TextStyle) -> str:
        """Convert content to HTML with style applied."""
        # Build style attributes
        styles = []
        
        if style.font_size == "small":
            styles.append("font-size: 14px")
        elif style.font_size == "large":
            styles.append("font-size: 20px")
        else:
            styles.append("font-size: 16px")
        
        if style.color:
            styles.append(f"color: {style.color}")
        
        if style.highlight:
            styles.append("background-color: #ffffd0")
        
        style_attr = "; ".join(styles)
        
        # Apply text formatting
        formatted = content
        if style.bold:
            formatted = f"<strong>{formatted}</strong>"
        if style.italic:
            formatted = f"<em>{formatted}</em>"
        
        # Wrap in paragraph with styles
        return f'<p style="{style_attr}">{formatted}</p>'
    
    def _to_markdown(self, content: str, style: TextStyle) -> str:
        """Convert content to Markdown with style hints."""
        formatted = content
        
        if style.bold:
            formatted = f"**{formatted}**"
        if style.italic:
            formatted = f"*{formatted}*"
        if style.highlight:
            formatted = f"=={formatted}=="  # Some markdown flavors support this
        
        return formatted
    
    def render_audio(
        self,
        content: str,
        voice: Optional[VoiceConfig] = None,
    ) -> bytes:
        """
        Generate audio representation of text via TTS.
        
        Requirements: 4.2 - Provide voice/audio explanations
        
        Args:
            content: The text content to convert to audio
            voice: Optional voice configuration
            
        Returns:
            Audio bytes
        """
        if not content:
            return b""
        
        voice = voice or self.default_voice_config
        return self.tts_service.synthesize(content, voice)
    
    def render_audio_url(
        self,
        content: str,
        voice: Optional[VoiceConfig] = None,
    ) -> str:
        """
        Generate audio and return URL.
        
        Requirements: 4.2 - Provide voice/audio explanations
        
        Args:
            content: The text content to convert to audio
            voice: Optional voice configuration
            
        Returns:
            URL to the audio file
        """
        if not content:
            return ""
        
        voice = voice or self.default_voice_config
        return self.tts_service.synthesize_to_url(content, voice)
    
    def render_visual_aid(
        self,
        visual_type: VisualType,
        data: VisualData,
    ) -> VisualAid:
        """
        Generate or retrieve a visual aid.
        
        Requirements: 4.3 - Generate or retrieve relevant diagrams and visual aids
        
        Args:
            visual_type: Type of visual to generate
            data: Data for generating the visual
            
        Returns:
            VisualAid with URL and metadata
        """
        url = ""
        alt_text = f"{visual_type.value} about {data.topic}"
        caption = data.description or f"Visual representation of {data.topic}"
        
        if visual_type == VisualType.DIAGRAM:
            url = self.image_service.generate_diagram(data.topic, data.description)
            alt_text = f"Diagram showing {data.topic}"
            
        elif visual_type == VisualType.CHART:
            if data.data_points:
                url = self.image_service.generate_chart(data.data_points, "bar")
            else:
                url = self.image_service.generate_chart({}, "bar")
            alt_text = f"Chart displaying {data.topic} data"
            
        elif visual_type == VisualType.IMAGE:
            keywords = data.keywords or [data.topic]
            url = self.image_service.search_image(keywords)
            alt_text = f"Image related to {data.topic}"
            
        elif visual_type == VisualType.FLOWCHART:
            url = self.image_service.generate_diagram(
                data.topic,
                f"Flowchart: {data.description}",
            )
            alt_text = f"Flowchart showing {data.topic} process"
            
        elif visual_type == VisualType.ANIMATION:
            # Animations would need special handling
            url = self.image_service.generate_diagram(
                data.topic,
                f"Animated: {data.description}",
            )
            alt_text = f"Animation demonstrating {data.topic}"
            
        elif visual_type == VisualType.ILLUSTRATION:
            keywords = data.keywords or [data.topic, "illustration", "educational"]
            url = self.image_service.search_image(keywords)
            alt_text = f"Illustration of {data.topic}"
        
        return VisualAid(
            type=visual_type,
            url=url,
            alt_text=alt_text,
            caption=caption,
            data={"topic": data.topic, "keywords": data.keywords},
        )
    
    def render_comprehension_buttons(
        self,
        options: list[ComprehensionOption],
        layout: str = "horizontal",
        spacing: str = "medium",
    ) -> ButtonGroup:
        """
        Create a button group for comprehension feedback.
        
        Requirements: 4.1 (part of text-based interaction support)
        
        Args:
            options: List of comprehension options
            layout: Button layout (horizontal/vertical)
            spacing: Spacing between buttons
            
        Returns:
            ButtonGroup with formatted buttons
        """
        return ButtonGroup(
            buttons=options,
            layout=layout,
            spacing=spacing,
        )
    
    def get_default_comprehension_options(self) -> list[ComprehensionOption]:
        """Get the standard comprehension feedback options."""
        return [
            ComprehensionOption(
                id="understood",
                label="I understood! ✓",
                icon="✓",
                value="understood",
            ),
            ComprehensionOption(
                id="partial",
                label="I partially understood",
                icon="~",
                value="partial",
            ),
            ComprehensionOption(
                id="not_understood",
                label="I didn't understand",
                icon="?",
                value="not_understood",
            ),
        ]
    
    def render_output_mode_buttons(self) -> ButtonGroup:
        """Get buttons for output mode selection."""
        options = [
            ComprehensionOption(
                id="more_examples",
                label="More examples",
                icon="📝",
                value="more_examples",
            ),
            ComprehensionOption(
                id="diagram",
                label="Show diagram",
                icon="📊",
                value="diagram",
            ),
            ComprehensionOption(
                id="slower_pace",
                label="Slower pace",
                icon="🐢",
                value="slower_pace",
            ),
            ComprehensionOption(
                id="simpler_words",
                label="Simpler words",
                icon="📖",
                value="simpler_words",
            ),
            ComprehensionOption(
                id="audio",
                label="Read aloud",
                icon="🔊",
                value="audio",
            ),
        ]
        return ButtonGroup(buttons=options, layout="horizontal", spacing="small")
    
    def get_available_voices(self) -> list[dict[str, str]]:
        """Get list of available TTS voices."""
        return self.tts_service.get_available_voices()
    
    def render_complete_response(
        self,
        text_content: str,
        include_audio: bool = False,
        include_visual: bool = False,
        visual_type: Optional[VisualType] = None,
        visual_topic: Optional[str] = None,
        include_comprehension_buttons: bool = True,
        text_style: Optional[TextStyle] = None,
        voice_config: Optional[VoiceConfig] = None,
    ) -> dict[str, Any]:
        """
        Render a complete multimodal response.
        
        Convenience method that combines text, audio, visual, and buttons.
        
        Args:
            text_content: The main text content
            include_audio: Whether to generate audio
            include_visual: Whether to include visual aid
            visual_type: Type of visual to generate
            visual_topic: Topic for visual generation
            include_comprehension_buttons: Whether to include feedback buttons
            text_style: Style for text rendering
            voice_config: Config for audio generation
            
        Returns:
            Dictionary with all rendered components
        """
        result: dict[str, Any] = {}
        
        # Always render text
        rendered_text = self.render_text(text_content, text_style)
        result["text"] = rendered_text
        result["message"] = rendered_text.content
        
        # Optionally render audio
        if include_audio and text_content:
            result["audio_url"] = self.render_audio_url(text_content, voice_config)
        
        # Optionally render visual
        if include_visual and visual_type and visual_topic:
            visual_data = VisualData(topic=visual_topic)
            result["visual_aid"] = self.render_visual_aid(visual_type, visual_data)
        
        # Optionally include comprehension buttons
        if include_comprehension_buttons:
            options = self.get_default_comprehension_options()
            result["comprehension_buttons"] = self.render_comprehension_buttons(options)
        
        return result
