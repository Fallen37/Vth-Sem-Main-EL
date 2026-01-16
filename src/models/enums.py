"""Enumeration types for the application."""

from enum import Enum


class UserRole(str, Enum):
    """User role enumeration."""

    STUDENT = "student"
    GUARDIAN = "guardian"
    ADMIN = "admin"


class Syllabus(str, Enum):
    """Syllabus type enumeration."""

    CBSE = "cbse"
    STATE = "state"


class ContentType(str, Enum):
    """Content type enumeration for uploaded documents."""

    TEXTBOOK = "textbook"
    NOTES = "notes"
    PAST_PAPER = "past_paper"
    QUESTION_BANK = "question_bank"


class DocumentStatus(str, Enum):
    """Document processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class InteractionSpeed(str, Enum):
    """Interaction speed preference."""

    SLOW = "slow"
    MEDIUM = "medium"
    FAST = "fast"


class InputType(str, Enum):
    """Input type for messages."""

    TEXT = "text"
    VOICE = "voice"
    IMAGE = "image"
    BUTTON = "button"


class MessageRole(str, Enum):
    """Message role indicating source."""

    STUDENT = "student"
    GUARDIAN = "guardian"
    AI = "ai"


class ComprehensionLevel(str, Enum):
    """Comprehension feedback level."""

    UNDERSTOOD = "understood"
    PARTIAL = "partial"
    NOT_UNDERSTOOD = "not_understood"


class FontSize(str, Enum):
    """Font size preference."""

    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
