# Data models package
"""Data models for the Autism Science Tutor application."""

from src.models.enums import (
    UserRole,
    Syllabus,
    ContentType,
    DocumentStatus,
    InteractionSpeed,
    InputType,
    MessageRole,
    ComprehensionLevel,
    FontSize,
)

from src.models.database import Base, get_db, init_db, engine, async_session_maker

from src.models.user import (
    UserORM,
    User,
    UserBase,
    UserCreate,
    UserUpdate,
)

from src.models.learning_profile import (
    LearningProfileORM,
    LearningProfile,
    LearningProfileBase,
    LearningProfileCreate,
    LearningProfileUpdate,
    OutputMode,
    ExplanationStyle,
    InterfacePreferences,
    TopicComprehension,
)

from src.models.session import (
    SessionORM,
    Session,
    SessionBase,
    SessionCreate,
    SessionUpdate,
    MessageORM,
    Message,
    MessageBase,
    MessageCreate,
)

from src.models.document import (
    DocumentORM,
    Document,
    DocumentBase,
    DocumentCreate,
    DocumentUpdate,
    ContentMetadata,
    ContentFilters,
)

from src.models.progress import (
    ProgressORM,
    Progress,
    ProgressBase,
    ProgressCreate,
    ProgressUpdate,
    AchievementORM,
    Achievement,
    AchievementBase,
    AchievementCreate,
    ProgressSummary,
    Topic,
)

__all__ = [
    # Enums
    "UserRole",
    "Syllabus",
    "ContentType",
    "DocumentStatus",
    "InteractionSpeed",
    "InputType",
    "MessageRole",
    "ComprehensionLevel",
    "FontSize",
    # Database
    "Base",
    "get_db",
    "init_db",
    "engine",
    "async_session_maker",
    # User
    "UserORM",
    "User",
    "UserBase",
    "UserCreate",
    "UserUpdate",
    # Learning Profile
    "LearningProfileORM",
    "LearningProfile",
    "LearningProfileBase",
    "LearningProfileCreate",
    "LearningProfileUpdate",
    "OutputMode",
    "ExplanationStyle",
    "InterfacePreferences",
    "TopicComprehension",
    # Session
    "SessionORM",
    "Session",
    "SessionBase",
    "SessionCreate",
    "SessionUpdate",
    "MessageORM",
    "Message",
    "MessageBase",
    "MessageCreate",
    # Document
    "DocumentORM",
    "Document",
    "DocumentBase",
    "DocumentCreate",
    "DocumentUpdate",
    "ContentMetadata",
    "ContentFilters",
    # Progress
    "ProgressORM",
    "Progress",
    "ProgressBase",
    "ProgressCreate",
    "ProgressUpdate",
    "AchievementORM",
    "Achievement",
    "AchievementBase",
    "AchievementCreate",
    "ProgressSummary",
    "Topic",
]
