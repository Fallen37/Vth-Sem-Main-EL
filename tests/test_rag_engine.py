"""Tests for RAGEngine - core retrieval and generation functionality."""

import pytest
from unittest.mock import MagicMock, patch

from src.services.rag_engine import (
    RAGEngine,
    RAGResponse,
    QueryContext,
    Chunk,
    Source,
)
from src.models.document import ContentFilters, CurriculumInfo
from src.models.enums import Syllabus


class TestRAGEngineCore:
    """Tests for RAGEngine core functionality."""

    @pytest.fixture
    def mock_embedding_service(self):
        """Create a mock embedding service."""
        mock = MagicMock()
        mock.embed_single.return_value = [0.1] * 384  # Typical embedding size
        return mock

    @pytest.fixture
    def mock_chroma_client(self):
        """Create a mock ChromaDB client."""
        mock = MagicMock()
        return mock

    @pytest.fixture
    def rag_engine(self, mock_embedding_service, mock_chroma_client):
        """Create a RAGEngine with mocked dependencies."""
        engine = RAGEngine(
            embedding_service=mock_embedding_service,
            chroma_client=mock_chroma_client,
            similarity_threshold=0.7,
            confidence_threshold=0.6,
            top_k=5,
        )
        return engine

    def test_retrieve_chunks_returns_chunks(self, rag_engine, mock_chroma_client):
        """Should retrieve and convert chunks from ChromaDB."""
        # Setup mock response
        mock_chroma_client.query.return_value = {
            "documents": [["Content about physics", "Content about chemistry"]],
            "metadatas": [[
                {"document_id": "doc1", "chunk_index": 0, "subject": "Physics"},
                {"document_id": "doc2", "chunk_index": 0, "subject": "Chemistry"},
            ]],
            "distances": [[0.2, 0.3]],  # Cosine distances
        }

        chunks = rag_engine.retrieve_chunks("What is force?")

        assert len(chunks) == 2
        assert chunks[0].content == "Content about physics"
        assert chunks[0].similarity == 0.8  # 1 - 0.2
        assert chunks[1].similarity == 0.7  # 1 - 0.3

    def test_retrieve_chunks_with_filters(self, rag_engine, mock_chroma_client, mock_embedding_service):
        """Should pass filters to ChromaDB query."""
        mock_chroma_client.query.return_value = {
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }

        filters = ContentFilters(grade=8, syllabus=Syllabus.CBSE)
        rag_engine.retrieve_chunks("What is force?", filters=filters)

        # Verify filters were passed
        mock_chroma_client.query.assert_called_once()
        call_args = mock_chroma_client.query.call_args
        assert call_args.kwargs["where"] is not None

    def test_retrieve_chunks_empty_results(self, rag_engine, mock_chroma_client):
        """Should handle empty results gracefully."""
        mock_chroma_client.query.return_value = {
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }

        chunks = rag_engine.retrieve_chunks("Unknown topic")
        assert chunks == []

    def test_filter_by_similarity_threshold(self, rag_engine):
        """Should filter chunks below similarity threshold."""
        chunks = [
            Chunk(content="High similarity", metadata={}, similarity=0.9),
            Chunk(content="Medium similarity", metadata={}, similarity=0.75),
            Chunk(content="Low similarity", metadata={}, similarity=0.5),
        ]

        filtered = rag_engine._filter_by_similarity_threshold(chunks)
        
        assert len(filtered) == 2
        assert all(c.similarity >= 0.7 for c in filtered)

    def test_calculate_confidence_no_chunks(self, rag_engine):
        """Should return 0 confidence for no chunks."""
        confidence = rag_engine._calculate_confidence([])
        assert confidence == 0.0

    def test_calculate_confidence_high_similarity(self, rag_engine):
        """Should return high confidence for high similarity chunks."""
        chunks = [
            Chunk(content="Content 1", metadata={}, similarity=0.95),
            Chunk(content="Content 2", metadata={}, similarity=0.90),
            Chunk(content="Content 3", metadata={}, similarity=0.85),
        ]

        confidence = rag_engine._calculate_confidence(chunks)
        assert confidence > 0.7

    def test_calculate_confidence_low_similarity(self, rag_engine):
        """Should return low confidence for low similarity chunks."""
        chunks = [
            Chunk(content="Content 1", metadata={}, similarity=0.3),
            Chunk(content="Content 2", metadata={}, similarity=0.2),
        ]

        confidence = rag_engine._calculate_confidence(chunks)
        assert confidence == 0.0  # All below threshold


class TestUncertaintyHandling:
    """Tests for uncertainty detection and handling."""

    @pytest.fixture
    def rag_engine(self):
        """Create a RAGEngine with mocked dependencies."""
        mock_embedding = MagicMock()
        mock_embedding.embed_single.return_value = [0.1] * 384
        mock_chroma = MagicMock()
        
        return RAGEngine(
            embedding_service=mock_embedding,
            chroma_client=mock_chroma,
            similarity_threshold=0.7,
            confidence_threshold=0.6,
            top_k=5,
        )

    def test_generate_uncertainty_message_very_low_confidence(self, rag_engine):
        """Should generate strong uncertainty message for very low confidence."""
        message = rag_engine._generate_uncertainty_message("What is X?", 0.2)
        
        assert "don't have enough information" in message
        assert "rephras" in message.lower()

    def test_generate_uncertainty_message_medium_confidence(self, rag_engine):
        """Should generate moderate uncertainty message for medium confidence."""
        message = rag_engine._generate_uncertainty_message("What is X?", 0.5)
        
        assert "not entirely sure" in message
        assert "verify" in message.lower()

    def test_generate_uncertainty_message_high_confidence(self, rag_engine):
        """Should return empty message for high confidence."""
        message = rag_engine._generate_uncertainty_message("What is X?", 0.8)
        assert message == ""

    def test_uncertainty_in_response(self, rag_engine):
        """Should include uncertainty indicators in response when confidence is low."""
        # Setup mock to return low similarity results
        rag_engine.chroma_client.query.return_value = {
            "documents": [["Some vaguely related content"]],
            "metadatas": [[{"document_id": "doc1", "chunk_index": 0}]],
            "distances": [[0.6]],  # Low similarity (0.4)
        }

        # Mock LLM to avoid actual API call
        with patch.object(rag_engine, '_generate_with_llm', return_value="Generated answer"):
            response = rag_engine.query("What is quantum entanglement?")

        assert response.has_uncertainty is True
        assert response.confidence < 0.6


class TestCurriculumPrioritization:
    """Tests for curriculum-based prioritization."""

    @pytest.fixture
    def rag_engine(self):
        """Create a RAGEngine with mocked dependencies."""
        mock_embedding = MagicMock()
        mock_embedding.embed_single.return_value = [0.1] * 384
        mock_chroma = MagicMock()
        
        return RAGEngine(
            embedding_service=mock_embedding,
            chroma_client=mock_chroma,
            similarity_threshold=0.7,
            confidence_threshold=0.6,
            top_k=5,
        )

    def test_apply_curriculum_boost_grade_match(self, rag_engine):
        """Should boost similarity for matching grade."""
        chunks = [
            Chunk(
                content="Physics content",
                metadata={"grade": 8, "syllabus": "cbse"},
                similarity=0.7,
            ),
        ]
        
        student_curriculum = CurriculumInfo(grade=8, syllabus=Syllabus.CBSE)
        boosted = rag_engine._apply_curriculum_boost(chunks, student_curriculum)
        
        # Grade match (+0.15) + Syllabus match (+0.10) = +0.25
        assert boosted[0].similarity == 0.95

    def test_apply_curriculum_boost_no_match(self, rag_engine):
        """Should not boost similarity for non-matching curriculum."""
        chunks = [
            Chunk(
                content="Physics content",
                metadata={"grade": 9, "syllabus": "state"},
                similarity=0.7,
            ),
        ]
        
        student_curriculum = CurriculumInfo(grade=8, syllabus=Syllabus.CBSE)
        boosted = rag_engine._apply_curriculum_boost(chunks, student_curriculum)
        
        # No match, no boost
        assert boosted[0].similarity == 0.7

    def test_apply_curriculum_boost_full_match(self, rag_engine):
        """Should apply maximum boost for full curriculum match."""
        chunks = [
            Chunk(
                content="Newton's Laws content",
                metadata={
                    "grade": 8,
                    "syllabus": "cbse",
                    "subject": "Physics",
                    "chapter": "Force",
                    "topic": "Newton's Laws",
                },
                similarity=0.6,
            ),
        ]
        
        student_curriculum = CurriculumInfo(
            grade=8,
            syllabus=Syllabus.CBSE,
            subject="Physics",
            chapter="Force",
            topic="Newton's Laws",
        )
        boosted = rag_engine._apply_curriculum_boost(chunks, student_curriculum)
        
        # Full match: +0.15 + 0.10 + 0.05 + 0.05 + 0.05 = +0.40
        # 0.6 + 0.40 = 1.0 (capped)
        assert boosted[0].similarity == 1.0

    def test_apply_curriculum_boost_caps_at_one(self, rag_engine):
        """Should cap boosted similarity at 1.0."""
        chunks = [
            Chunk(
                content="Content",
                metadata={"grade": 8, "syllabus": "cbse"},
                similarity=0.95,
            ),
        ]
        
        student_curriculum = CurriculumInfo(grade=8, syllabus=Syllabus.CBSE)
        boosted = rag_engine._apply_curriculum_boost(chunks, student_curriculum)
        
        assert boosted[0].similarity == 1.0

    def test_map_question_to_curriculum_no_results(self, rag_engine):
        """Should return empty mapping when no chunks found."""
        rag_engine.chroma_client.query.return_value = {
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }

        mapping = rag_engine.map_question_to_curriculum("Unknown topic")
        
        assert mapping["mapped"] is False
        assert mapping["chapters"] == []
        assert mapping["topics"] == []

    def test_map_question_to_curriculum_with_results(self, rag_engine):
        """Should extract curriculum mapping from chunks."""
        rag_engine.chroma_client.query.return_value = {
            "documents": [["Content 1", "Content 2"]],
            "metadatas": [[
                {"chapter": "Force", "topic": "Newton's Laws", "subject": "Physics"},
                {"chapter": "Force", "topic": "Friction", "subject": "Physics"},
            ]],
            "distances": [[0.2, 0.25]],  # High similarity
        }

        mapping = rag_engine.map_question_to_curriculum("What is force?")
        
        assert mapping["mapped"] is True
        assert len(mapping["chapters"]) > 0
        assert mapping["primary_chapter"] == "Force"


class TestSourceBuilding:
    """Tests for source reference building."""

    @pytest.fixture
    def rag_engine(self):
        """Create a RAGEngine."""
        return RAGEngine(
            embedding_service=MagicMock(),
            chroma_client=MagicMock(),
        )

    def test_build_sources(self, rag_engine):
        """Should build source references from chunks."""
        chunks = [
            Chunk(
                content="This is content about physics that explains Newton's laws in detail.",
                metadata={
                    "document_id": "doc123",
                    "chunk_index": 5,
                    "grade": 8,
                    "syllabus": "cbse",
                    "subject": "Physics",
                    "chapter": "Force",
                    "topic": "Newton's Laws",
                },
                similarity=0.85,
            ),
        ]

        sources = rag_engine._build_sources(chunks)

        assert len(sources) == 1
        assert sources[0].document_id == "doc123"
        assert sources[0].chunk_index == 5
        assert sources[0].similarity == 0.85
        assert sources[0].grade == 8
        assert sources[0].chapter == "Force"

    def test_build_sources_truncates_preview(self, rag_engine):
        """Should truncate long content in preview."""
        long_content = "A" * 300
        chunks = [
            Chunk(
                content=long_content,
                metadata={"document_id": "doc1", "chunk_index": 0},
                similarity=0.8,
            ),
        ]

        sources = rag_engine._build_sources(chunks)

        assert len(sources[0].content_preview) == 203  # 200 + "..."
        assert sources[0].content_preview.endswith("...")


class TestFollowUpGeneration:
    """Tests for follow-up question generation."""

    @pytest.fixture
    def rag_engine(self):
        """Create a RAGEngine."""
        return RAGEngine(
            embedding_service=MagicMock(),
            chroma_client=MagicMock(),
        )

    def test_generate_follow_ups_with_topics(self, rag_engine):
        """Should generate follow-ups based on topics."""
        chunks = [
            Chunk(
                content="Content",
                metadata={"topic": "Newton's Laws", "chapter": "Force"},
                similarity=0.8,
            ),
        ]

        follow_ups = rag_engine._generate_follow_ups("What is force?", chunks)

        assert len(follow_ups) > 0
        assert len(follow_ups) <= 5
        # Should include topic-based suggestions
        assert any("Newton's Laws" in f for f in follow_ups)

    def test_generate_follow_ups_empty_chunks(self, rag_engine):
        """Should generate generic follow-ups for empty chunks."""
        follow_ups = rag_engine._generate_follow_ups("What is force?", [])

        assert len(follow_ups) > 0
        # Should include generic suggestions
        assert any("example" in f.lower() for f in follow_ups)


class TestQueryContext:
    """Tests for QueryContext model."""

    def test_query_context_defaults(self):
        """Should have sensible defaults."""
        context = QueryContext()
        
        assert context.student_id is None
        assert context.grade is None
        assert context.syllabus is None
        assert context.conversation_history == []

    def test_query_context_with_values(self):
        """Should accept all values."""
        from uuid import uuid4
        
        student_id = uuid4()
        context = QueryContext(
            student_id=student_id,
            grade=8,
            syllabus=Syllabus.CBSE,
            conversation_history=[{"role": "user", "content": "Hello"}],
        )
        
        assert context.student_id == student_id
        assert context.grade == 8
        assert context.syllabus == Syllabus.CBSE
        assert len(context.conversation_history) == 1
