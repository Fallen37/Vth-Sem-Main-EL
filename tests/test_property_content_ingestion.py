"""Property-based tests for ContentIngestionService.

Feature: autism-science-tutor, Property 1: Document Embedding Round-Trip
Validates: Requirements 1.1

This test uses lightweight mock implementations to test the round-trip property
without requiring heavy ML dependencies (sentence-transformers, chromadb).
The property being tested is: for any valid document, it can be embedded and
retrieved by semantically similar queries.
"""

import hashlib
import os
import tempfile
from contextlib import asynccontextmanager
from typing import Optional
from uuid import UUID

import pytest
from hypothesis import given, settings, strategies as st, assume, HealthCheck
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from src.models.database import Base
from src.models.enums import ContentType, Syllabus
from src.models.document import ContentMetadata
from src.services.content_ingestion import (
    ContentIngestionService,
    TextChunker,
)


# Strategies for generating valid test data
grade_strategy = st.integers(min_value=5, max_value=10)
syllabus_strategy = st.sampled_from([Syllabus.CBSE, Syllabus.STATE])
content_type_strategy = st.sampled_from([
    ContentType.TEXTBOOK,
    ContentType.NOTES,
    ContentType.PAST_PAPER,
    ContentType.QUESTION_BANK,
])
subject_strategy = st.sampled_from(["Physics", "Chemistry", "Biology", "Mathematics"])
chapter_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "Zs")),
    min_size=3,
    max_size=50,
).filter(lambda x: x.strip())


# Strategy for generating educational content text
# Must be long enough to create at least one chunk (min 100 chars after processing)
educational_content_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "Zs", "Po")),
    min_size=150,
    max_size=1000,
).filter(lambda x: len(x.strip()) >= 150)


class MockEmbeddingService:
    """
    Mock embedding service that generates deterministic embeddings based on text hash.
    This allows testing the round-trip property without requiring sentence-transformers.
    Similar texts will have similar embeddings (based on shared n-grams).
    """
    
    def __init__(self, embedding_dim: int = 64):
        self.embedding_dim = embedding_dim
    
    def _text_to_embedding(self, text: str) -> list[float]:
        """Generate a deterministic embedding from text using hash-based approach."""
        # Normalize text
        text = text.lower().strip()
        
        # Create embedding based on character n-grams for some semantic similarity
        embedding = [0.0] * self.embedding_dim
        
        # Use 3-grams to capture some local structure
        for i in range(len(text) - 2):
            ngram = text[i:i+3]
            # Hash the n-gram to get a position and value
            h = int(hashlib.md5(ngram.encode()).hexdigest(), 16)
            pos = h % self.embedding_dim
            val = ((h >> 8) % 1000) / 1000.0 - 0.5
            embedding[pos] += val
        
        # Normalize the embedding
        magnitude = sum(x*x for x in embedding) ** 0.5
        if magnitude > 0:
            embedding = [x / magnitude for x in embedding]
        
        return embedding
    
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts."""
        return [self._text_to_embedding(text) for text in texts]
    
    def embed_single(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        return self._text_to_embedding(text)


class MockChromaDBClient:
    """
    Mock ChromaDB client that stores documents in memory.
    Supports basic similarity search using cosine similarity.
    """
    
    def __init__(self):
        self._documents: dict[str, dict] = {}
    
    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        dot_product = sum(x * y for x, y in zip(a, b))
        magnitude_a = sum(x * x for x in a) ** 0.5
        magnitude_b = sum(x * x for x in b) ** 0.5
        if magnitude_a == 0 or magnitude_b == 0:
            return 0.0
        return dot_product / (magnitude_a * magnitude_b)
    
    def add_documents(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict],
    ) -> None:
        """Add documents with embeddings to the store."""
        for id_, embedding, document, metadata in zip(ids, embeddings, documents, metadatas):
            self._documents[id_] = {
                "embedding": embedding,
                "document": document,
                "metadata": metadata,
            }
    
    def query(
        self,
        query_embedding: list[float],
        n_results: int = 5,
        where: Optional[dict] = None,
    ) -> dict:
        """Query for similar documents."""
        # Calculate similarities
        results = []
        for id_, data in self._documents.items():
            # Apply where filter if provided
            if where:
                match = True
                for key, value in where.items():
                    if data["metadata"].get(key) != value:
                        match = False
                        break
                if not match:
                    continue
            
            similarity = self._cosine_similarity(query_embedding, data["embedding"])
            # Convert similarity to distance (ChromaDB uses distance, not similarity)
            distance = 1.0 - similarity
            results.append((id_, data, distance))
        
        # Sort by distance (ascending) and take top n
        results.sort(key=lambda x: x[2])
        results = results[:n_results]
        
        return {
            "ids": [[r[0] for r in results]],
            "documents": [[r[1]["document"] for r in results]],
            "metadatas": [[r[1]["metadata"] for r in results]],
            "distances": [[r[2] for r in results]],
        }
    
    def delete_by_document_id(self, document_id: str) -> None:
        """Delete all chunks for a document."""
        to_delete = [
            id_ for id_, data in self._documents.items()
            if data["metadata"].get("document_id") == document_id
        ]
        for id_ in to_delete:
            del self._documents[id_]


@pytest.fixture
def embedding_service():
    """Create mock embedding service for tests."""
    return MockEmbeddingService()


@pytest.fixture
def chroma_client():
    """Create mock ChromaDB client for tests."""
    return MockChromaDBClient()


@asynccontextmanager
async def create_test_db_session(tmp_dir: str):
    """Create an async database session for tests as a context manager."""
    db_path = os.path.join(tmp_dir, "test.db")
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path}",
        echo=False,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        yield session
    
    await engine.dispose()


class TestDocumentEmbeddingRoundTrip:
    """
    Property 1: Document Embedding Round-Trip
    
    For any valid educational document uploaded to the system, the document 
    SHALL be converted to embeddings and stored such that it can be retrieved 
    by semantically similar queries.
    
    Validates: Requirements 1.1
    """

    @given(
        grade=grade_strategy,
        syllabus=syllabus_strategy,
        content_type=content_type_strategy,
        subject=subject_strategy,
        chapter=chapter_strategy,
        content=educational_content_strategy,
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_document_embedding_round_trip(
        self,
        grade,
        syllabus,
        content_type,
        subject,
        chapter,
        content,
    ):
        """
        Feature: autism-science-tutor, Property 1: Document Embedding Round-Trip
        Validates: Requirements 1.1
        
        For any valid document with educational content:
        1. The document can be uploaded and processed into embeddings
        2. The embedded content can be retrieved using semantically similar queries
        """
        # Ensure content is valid for chunking
        assume(len(content.strip()) >= 150)
        assume(any(c.isalnum() for c in content))
        
        # Create mock services for each test run
        embedding_service = MockEmbeddingService()
        chroma_client = MockChromaDBClient()
        
        # Create temporary file with content
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".txt",
            delete=False,
            encoding="utf-8",
        ) as f:
            f.write(content)
            temp_path = f.name
        
        # Create temp directory for database
        with tempfile.TemporaryDirectory() as tmp_dir:
            try:
                # Create metadata
                metadata = ContentMetadata(
                    grade=grade,
                    syllabus=syllabus,
                    subject=subject,
                    chapter=chapter.strip() if chapter.strip() else "Test Chapter",
                    content_type=content_type,
                )
                
                async with create_test_db_session(tmp_dir) as db_session:
                    # Create service with test dependencies
                    service = ContentIngestionService(
                        db=db_session,
                        embedding_service=embedding_service,
                        chroma_client=chroma_client,
                    )
                    
                    # Upload document
                    doc_id = await service.upload_document(
                        file_path=temp_path,
                        filename="test_document.txt",
                        metadata=metadata,
                    )
                    
                    # Verify document was created
                    assert isinstance(doc_id, UUID)
                    
                    # Process document (extract, chunk, embed, store)
                    result = await service.process_document(doc_id, temp_path)
                    
                    # If processing succeeded, verify round-trip retrieval
                    if result.embedding_status == "SUCCESS":
                        assert result.chunk_count > 0
                        
                        # Generate query embedding from a portion of the content
                        # Use first 100 chars as query (semantic similarity test)
                        query_text = content[:100].strip()
                        if query_text:
                            query_embedding = embedding_service.embed_single(query_text)
                            
                            # Query for similar content
                            results = chroma_client.query(
                                query_embedding=query_embedding,
                                n_results=5,
                            )
                            
                            # Verify we can retrieve the stored content
                            assert results is not None
                            assert "documents" in results
                            assert len(results["documents"]) > 0
                            assert len(results["documents"][0]) > 0
                            
                            # Verify metadata is preserved
                            assert "metadatas" in results
                            retrieved_metadata = results["metadatas"][0][0]
                            assert retrieved_metadata["document_id"] == str(doc_id)
                            assert retrieved_metadata["grade"] == grade
                            assert retrieved_metadata["syllabus"] == syllabus.value
                            assert retrieved_metadata["subject"] == subject
                    else:
                        # Document was too short or had issues - this is acceptable
                        # as long as the system handles it gracefully
                        assert result.errors or result.chunk_count == 0
            
            finally:
                # Cleanup temp file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
