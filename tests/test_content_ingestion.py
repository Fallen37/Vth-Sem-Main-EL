"""Tests for ContentIngestionService - TextChunker and TextExtractor."""

import os
import tempfile

import pytest

from src.services.content_ingestion import (
    TextChunker,
    TextExtractor,
)
from src.models.document import (
    ContentMetadata,
    ContentFilters,
    CurriculumInfo,
    VALID_GRADE_MIN,
    VALID_GRADE_MAX,
)
from src.models.enums import ContentType, Syllabus


@pytest.fixture
def temp_txt_file():
    """Create a temporary text file for testing."""
    content = """
    Newton's First Law of Motion states that an object at rest stays at rest and an object 
    in motion stays in motion with the same speed and in the same direction unless acted 
    upon by an unbalanced force. This is also known as the law of inertia.
    
    Newton's Second Law of Motion states that the acceleration of an object depends on 
    the mass of the object and the amount of force applied. The formula is F = ma, where 
    F is force, m is mass, and a is acceleration.
    
    Newton's Third Law of Motion states that for every action, there is an equal and 
    opposite reaction. When one object exerts a force on a second object, the second 
    object exerts an equal force in the opposite direction on the first object.
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(content)
        temp_path = f.name
    yield temp_path
    os.unlink(temp_path)


class TestTextChunker:
    """Tests for TextChunker."""

    def test_chunk_empty_text(self):
        """Empty text should return empty list."""
        chunker = TextChunker()
        assert chunker.chunk("") == []
        assert chunker.chunk("   ") == []

    def test_chunk_short_text(self):
        """Short text below min_chunk_size should return empty list."""
        chunker = TextChunker(chunk_size=500, min_chunk_size=100)
        assert chunker.chunk("Short text") == []

    def test_chunk_single_chunk(self):
        """Text within chunk_size should return single chunk."""
        chunker = TextChunker(chunk_size=500, min_chunk_size=50)
        text = "This is a test sentence that is long enough to be a valid chunk."
        chunks = chunker.chunk(text)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_chunk_multiple_chunks(self):
        """Long text should be split into multiple chunks."""
        chunker = TextChunker(chunk_size=100, chunk_overlap=20, min_chunk_size=50)
        text = "This is sentence one. " * 20  # Long enough for multiple chunks
        chunks = chunker.chunk(text)
        assert len(chunks) > 1

    def test_chunk_overlap(self):
        """Chunks should have overlap."""
        chunker = TextChunker(chunk_size=100, chunk_overlap=30, min_chunk_size=30)
        text = "Word " * 100  # Long text
        chunks = chunker.chunk(text)
        # With overlap, later chunks should start before previous chunk ends
        assert len(chunks) > 1


class TestTextExtractor:
    """Tests for TextExtractor."""

    def test_extract_txt(self, temp_txt_file):
        """Should extract text from TXT file."""
        text = TextExtractor.extract(temp_txt_file)
        assert "Newton" in text
        assert "inertia" in text

    def test_unsupported_format(self):
        """Should raise error for unsupported format."""
        with pytest.raises(ValueError, match="Unsupported file format"):
            TextExtractor.extract("test.xyz")


class TestContentMetadata:
    """Tests for ContentMetadata model with curriculum fields."""

    def test_valid_metadata_with_topic_and_tags(self):
        """Should create metadata with topic and tags."""
        metadata = ContentMetadata(
            grade=8,
            syllabus=Syllabus.CBSE,
            subject="Physics",
            chapter="Force and Laws of Motion",
            topic="Newton's Laws",
            tags=["mechanics", "motion", "force"],
            content_type=ContentType.TEXTBOOK,
        )
        assert metadata.grade == 8
        assert metadata.syllabus == Syllabus.CBSE
        assert metadata.topic == "Newton's Laws"
        assert metadata.tags == ["mechanics", "motion", "force"]

    def test_metadata_without_optional_fields(self):
        """Should create metadata without optional topic and tags."""
        metadata = ContentMetadata(
            grade=6,
            syllabus=Syllabus.STATE,
            subject="Biology",
            chapter="Living Organisms",
            content_type=ContentType.NOTES,
        )
        assert metadata.topic is None
        assert metadata.tags == []

    def test_grade_validation_min(self):
        """Should reject grade below minimum."""
        with pytest.raises(ValueError):
            ContentMetadata(
                grade=4,  # Below minimum of 5
                syllabus=Syllabus.CBSE,
                subject="Physics",
                chapter="Test",
                content_type=ContentType.TEXTBOOK,
            )

    def test_grade_validation_max(self):
        """Should reject grade above maximum."""
        with pytest.raises(ValueError):
            ContentMetadata(
                grade=11,  # Above maximum of 10
                syllabus=Syllabus.CBSE,
                subject="Physics",
                chapter="Test",
                content_type=ContentType.TEXTBOOK,
            )

    def test_tags_normalization(self):
        """Tags should be normalized to lowercase and stripped."""
        metadata = ContentMetadata(
            grade=7,
            syllabus=Syllabus.CBSE,
            subject="Chemistry",
            chapter="Atoms",
            tags=["  CHEMISTRY  ", "Atoms", "  elements  "],
            content_type=ContentType.TEXTBOOK,
        )
        assert metadata.tags == ["chemistry", "atoms", "elements"]

    def test_empty_tags_filtered(self):
        """Empty tags should be filtered out."""
        metadata = ContentMetadata(
            grade=7,
            syllabus=Syllabus.CBSE,
            subject="Chemistry",
            chapter="Atoms",
            tags=["valid", "", "  ", "another"],
            content_type=ContentType.TEXTBOOK,
        )
        assert metadata.tags == ["valid", "another"]


class TestContentFilters:
    """Tests for ContentFilters model."""

    def test_empty_filters(self):
        """Empty filters should produce no ChromaDB filter."""
        filters = ContentFilters()
        assert filters.to_chroma_filter() is None

    def test_single_filter(self):
        """Single filter should produce simple where clause."""
        filters = ContentFilters(grade=8)
        chroma_filter = filters.to_chroma_filter()
        assert chroma_filter == {"grade": 8}

    def test_multiple_filters(self):
        """Multiple filters should produce $and clause."""
        filters = ContentFilters(
            grade=8,
            syllabus=Syllabus.CBSE,
            subject="Physics",
        )
        chroma_filter = filters.to_chroma_filter()
        assert "$and" in chroma_filter
        conditions = chroma_filter["$and"]
        assert {"grade": 8} in conditions
        assert {"syllabus": "cbse"} in conditions
        assert {"subject": "Physics"} in conditions

    def test_topic_filter(self):
        """Topic filter should be included in ChromaDB filter."""
        filters = ContentFilters(topic="Newton's Laws")
        chroma_filter = filters.to_chroma_filter()
        assert chroma_filter == {"topic": "Newton's Laws"}


class TestCurriculumInfo:
    """Tests for CurriculumInfo model."""

    def test_exact_match(self):
        """Should match when grade and syllabus are the same."""
        info1 = CurriculumInfo(grade=8, syllabus=Syllabus.CBSE)
        info2 = CurriculumInfo(grade=8, syllabus=Syllabus.CBSE)
        assert info1.matches(info2)

    def test_no_match_different_grade(self):
        """Should not match when grades differ."""
        info1 = CurriculumInfo(grade=8, syllabus=Syllabus.CBSE)
        info2 = CurriculumInfo(grade=9, syllabus=Syllabus.CBSE)
        assert not info1.matches(info2)

    def test_no_match_different_syllabus(self):
        """Should not match when syllabus differs."""
        info1 = CurriculumInfo(grade=8, syllabus=Syllabus.CBSE)
        info2 = CurriculumInfo(grade=8, syllabus=Syllabus.STATE)
        assert not info1.matches(info2)

    def test_partial_match_full(self):
        """Full match should return 1.0."""
        info1 = CurriculumInfo(
            grade=8,
            syllabus=Syllabus.CBSE,
            subject="Physics",
            chapter="Force",
            topic="Newton's Laws",
        )
        info2 = CurriculumInfo(
            grade=8,
            syllabus=Syllabus.CBSE,
            subject="Physics",
            chapter="Force",
            topic="Newton's Laws",
        )
        assert info1.matches_partial(info2) == 1.0

    def test_partial_match_grade_syllabus_only(self):
        """Partial match with only grade and syllabus should return 0.4."""
        info1 = CurriculumInfo(grade=8, syllabus=Syllabus.CBSE)
        info2 = CurriculumInfo(grade=8, syllabus=Syllabus.CBSE)
        assert info1.matches_partial(info2) == 0.4  # 2/5 = 0.4

    def test_partial_match_no_match(self):
        """No match should return 0.0."""
        info1 = CurriculumInfo(grade=8, syllabus=Syllabus.CBSE)
        info2 = CurriculumInfo(grade=9, syllabus=Syllabus.STATE)
        assert info1.matches_partial(info2) == 0.0


class TestGradeConstants:
    """Tests for grade range constants."""

    def test_valid_grade_range(self):
        """Grade range should be 5-10 for Indian curriculum."""
        assert VALID_GRADE_MIN == 5
        assert VALID_GRADE_MAX == 10
