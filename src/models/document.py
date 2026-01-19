"""Document model - SQLAlchemy and Pydantic schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import String, Integer, DateTime, Enum as SQLEnum, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.models.database import Base
from src.models.enums import ContentType, DocumentStatus, Syllabus


# Valid grade range for Indian curriculum (grades 5-10)
VALID_GRADE_MIN = 5
VALID_GRADE_MAX = 10


# SQLAlchemy Model
class DocumentORM(Base):
    """SQLAlchemy Document model."""

    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(SQLEnum(ContentType), nullable=False)
    grade: Mapped[int] = mapped_column(Integer, nullable=False)
    syllabus: Mapped[str] = mapped_column(SQLEnum(Syllabus), nullable=False)
    subject: Mapped[str] = mapped_column(String(100), nullable=False)
    chapter: Mapped[str] = mapped_column(String(255), nullable=False)
    topic: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Actual document content
    tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON-encoded list of tags
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(
        SQLEnum(DocumentStatus), nullable=False, default=DocumentStatus.PENDING.value
    )


# Pydantic Schemas
class ContentMetadata(BaseModel):
    """Content metadata for document uploads."""

    grade: int = Field(ge=VALID_GRADE_MIN, le=VALID_GRADE_MAX, description="Grade level (5-10)")
    syllabus: Syllabus = Field(description="Syllabus type (CBSE or State)")
    subject: str = Field(min_length=1, description="Subject name")
    chapter: str = Field(min_length=1, description="Chapter name")
    topic: Optional[str] = Field(default=None, description="Specific topic within the chapter")
    tags: list[str] = Field(default_factory=list, description="Additional tags for categorization")
    content_type: ContentType = Field(description="Type of content")

    @field_validator("grade")
    @classmethod
    def validate_grade(cls, v: int) -> int:
        """Validate grade is within Indian curriculum range (5-10)."""
        if not VALID_GRADE_MIN <= v <= VALID_GRADE_MAX:
            raise ValueError(f"Grade must be between {VALID_GRADE_MIN} and {VALID_GRADE_MAX}")
        return v

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        """Validate and normalize tags."""
        return [tag.strip().lower() for tag in v if tag.strip()]


class DocumentBase(BaseModel):
    """Base document schema."""

    filename: str
    content_type: ContentType
    grade: int = Field(ge=VALID_GRADE_MIN, le=VALID_GRADE_MAX)
    syllabus: Syllabus
    subject: str
    chapter: str
    topic: Optional[str] = None
    tags: list[str] = Field(default_factory=list)


class DocumentCreate(DocumentBase):
    """Schema for creating a document."""

    pass


class DocumentUpdate(BaseModel):
    """Schema for updating a document."""

    chunk_count: Optional[int] = None
    processed_at: Optional[datetime] = None
    status: Optional[DocumentStatus] = None
    topic: Optional[str] = None
    tags: Optional[list[str]] = None


class Document(DocumentBase):
    """Full document schema."""

    id: UUID
    chunk_count: int = 0
    uploaded_at: datetime
    processed_at: Optional[datetime] = None
    status: DocumentStatus = DocumentStatus.PENDING

    class Config:
        from_attributes = True


class ContentFilters(BaseModel):
    """Filters for content queries."""

    grade: Optional[int] = Field(None, ge=VALID_GRADE_MIN, le=VALID_GRADE_MAX)
    syllabus: Optional[Syllabus] = None
    subject: Optional[str] = None
    chapter: Optional[str] = None
    topic: Optional[str] = None
    tags: Optional[list[str]] = None
    content_type: Optional[ContentType] = None

    def to_chroma_filter(self) -> Optional[dict]:
        """Convert filters to ChromaDB where clause format."""
        conditions = []
        
        if self.grade is not None:
            conditions.append({"grade": self.grade})
        if self.syllabus is not None:
            conditions.append({"syllabus": self.syllabus.value})
        if self.subject is not None:
            conditions.append({"subject": self.subject})
        if self.chapter is not None:
            conditions.append({"chapter": self.chapter})
        if self.topic is not None:
            conditions.append({"topic": self.topic})
        if self.content_type is not None:
            conditions.append({"content_type": self.content_type.value})
        
        if not conditions:
            return None
        if len(conditions) == 1:
            return conditions[0]
        return {"$and": conditions}


class CurriculumInfo(BaseModel):
    """Curriculum information for a document or query."""

    grade: int = Field(ge=VALID_GRADE_MIN, le=VALID_GRADE_MAX)
    syllabus: Syllabus
    subject: Optional[str] = None
    chapter: Optional[str] = None
    topic: Optional[str] = None

    def matches(self, other: "CurriculumInfo") -> bool:
        """Check if this curriculum info matches another (for prioritization)."""
        if self.grade != other.grade:
            return False
        if self.syllabus != other.syllabus:
            return False
        return True

    def matches_partial(self, other: "CurriculumInfo") -> float:
        """Calculate partial match score (0.0 to 1.0) for curriculum prioritization."""
        score = 0.0
        max_score = 5.0  # grade, syllabus, subject, chapter, topic
        
        if self.grade == other.grade:
            score += 1.0
        if self.syllabus == other.syllabus:
            score += 1.0
        if self.subject and other.subject and self.subject.lower() == other.subject.lower():
            score += 1.0
        if self.chapter and other.chapter and self.chapter.lower() == other.chapter.lower():
            score += 1.0
        if self.topic and other.topic and self.topic.lower() == other.topic.lower():
            score += 1.0
        
        return score / max_score
