"""Property-based tests for RAGEngine.

Feature: autism-science-tutor, Property 2: RAG Retrieval Relevance
Validates: Requirements 1.2

This test validates that for any question asked by a student where relevant 
content exists in the Content_Store, the retrieved chunks SHALL have a 
semantic similarity score above the configured threshold to the question.
"""

import hashlib
from typing import Optional

import pytest
from hypothesis import given, settings, strategies as st, assume, HealthCheck

from src.services.rag_engine import RAGEngine, Chunk
from src.models.document import ContentFilters
from src.models.enums import Syllabus


# Strategies for generating valid test data
grade_strategy = st.integers(min_value=5, max_value=10)
syllabus_strategy = st.sampled_from([Syllabus.CBSE, Syllabus.STATE])
subject_strategy = st.sampled_from(["Physics", "Chemistry", "Biology", "Mathematics"])
chapter_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "Zs")),
    min_size=3,
    max_size=30,
).filter(lambda x: x.strip())

# Strategy for generating educational content
educational_content_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "Zs", "Po")),
    min_size=50,
    max_size=500,
).filter(lambda x: len(x.strip()) >= 50 and any(c.isalnum() for c in x))


class MockEmbeddingService:
    """
    Mock embedding service that generates deterministic embeddings based on text hash.
    Similar texts will have similar embeddings (based on shared n-grams).
    """
    
    def __init__(self, embedding_dim: int = 64):
        self.embedding_dim = embedding_dim
    
    def _text_to_embedding(self, text: str) -> list[float]:
        """Generate a deterministic embedding from text using hash-based approach."""
        text = text.lower().strip()
        embedding = [0.0] * self.embedding_dim
        
        # Use 3-grams to capture some local structure
        for i in range(len(text) - 2):
            ngram = text[i:i+3]
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
        results = []
        for id_, data in self._documents.items():
            if where:
                match = self._check_where_filter(data["metadata"], where)
                if not match:
                    continue
            
            similarity = self._cosine_similarity(query_embedding, data["embedding"])
            distance = 1.0 - similarity
            results.append((id_, data, distance))
        
        results.sort(key=lambda x: x[2])
        results = results[:n_results]
        
        return {
            "ids": [[r[0] for r in results]],
            "documents": [[r[1]["document"] for r in results]],
            "metadatas": [[r[1]["metadata"] for r in results]],
            "distances": [[r[2] for r in results]],
        }
    
    def _check_where_filter(self, metadata: dict, where: dict) -> bool:
        """Check if metadata matches the where filter."""
        if "$and" in where:
            return all(self._check_where_filter(metadata, cond) for cond in where["$and"])
        for key, value in where.items():
            if key.startswith("$"):
                continue
            if metadata.get(key) != value:
                return False
        return True
    
    def clear(self) -> None:
        """Clear all documents."""
        self._documents.clear()


class TestRAGRetrievalRelevance:
    """
    Property 2: RAG Retrieval Relevance
    
    For any question asked by a student where relevant content exists in the 
    Content_Store, the retrieved chunks SHALL have a semantic similarity score 
    above the configured threshold to the question.
    
    Validates: Requirements 1.2
    """

    @pytest.fixture
    def embedding_service(self):
        """Create mock embedding service."""
        return MockEmbeddingService()

    @pytest.fixture
    def chroma_client(self):
        """Create mock ChromaDB client."""
        return MockChromaDBClient()

    @pytest.fixture
    def rag_engine(self, embedding_service, chroma_client):
        """Create RAGEngine with mock dependencies."""
        return RAGEngine(
            embedding_service=embedding_service,
            chroma_client=chroma_client,
            similarity_threshold=0.5,
            confidence_threshold=0.6,
            top_k=5,
        )

    def _store_content(
        self,
        chroma_client: MockChromaDBClient,
        embedding_service: MockEmbeddingService,
        content: str,
        metadata: dict,
        doc_id: str = "test_doc",
    ) -> None:
        """Helper to store content in the mock ChromaDB."""
        embedding = embedding_service.embed_single(content)
        chroma_client.add_documents(
            ids=[f"{doc_id}_chunk_0"],
            embeddings=[embedding],
            documents=[content],
            metadatas=[metadata],
        )

    @given(
        content=educational_content_strategy,
        grade=grade_strategy,
        syllabus=syllabus_strategy,
        subject=subject_strategy,
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_rag_retrieval_relevance_exact_query(
        self,
        content: str,
        grade: int,
        syllabus: Syllabus,
        subject: str,
    ):
        """
        Feature: autism-science-tutor, Property 2: RAG Retrieval Relevance
        Validates: Requirements 1.2
        
        For any content stored in the system, querying with the exact same 
        content should return chunks with high similarity scores.
        """
        assume(len(content.strip()) >= 50)
        assume(any(c.isalnum() for c in content))
        
        # Create fresh mock services for each test
        embedding_service = MockEmbeddingService()
        chroma_client = MockChromaDBClient()
        
        rag_engine = RAGEngine(
            embedding_service=embedding_service,
            chroma_client=chroma_client,
            similarity_threshold=0.5,
            confidence_threshold=0.6,
            top_k=5,
        )
        
        # Store the content
        metadata = {
            "document_id": "test_doc",
            "chunk_index": 0,
            "grade": grade,
            "syllabus": syllabus.value,
            "subject": subject,
            "chapter": "Test Chapter",
        }
        self._store_content(chroma_client, embedding_service, content, metadata)
        
        # Query with the exact same content
        chunks = rag_engine.retrieve_chunks(content)
        
        # Property: Retrieved chunks should have similarity above threshold
        assert len(chunks) > 0, "Should retrieve at least one chunk"
        
        # The exact same content should have very high similarity (close to 1.0)
        best_chunk = chunks[0]
        assert best_chunk.similarity >= rag_engine.similarity_threshold, (
            f"Best chunk similarity {best_chunk.similarity} should be >= "
            f"threshold {rag_engine.similarity_threshold}"
        )

    @given(
        content=educational_content_strategy,
        grade=grade_strategy,
        syllabus=syllabus_strategy,
        subject=subject_strategy,
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_rag_retrieval_relevance_partial_query(
        self,
        content: str,
        grade: int,
        syllabus: Syllabus,
        subject: str,
    ):
        """
        Feature: autism-science-tutor, Property 2: RAG Retrieval Relevance
        Validates: Requirements 1.2
        
        For any content stored in the system, querying with a portion of that 
        content should return chunks with similarity scores above threshold.
        """
        assume(len(content.strip()) >= 100)
        assume(any(c.isalnum() for c in content))
        
        # Create fresh mock services
        embedding_service = MockEmbeddingService()
        chroma_client = MockChromaDBClient()
        
        rag_engine = RAGEngine(
            embedding_service=embedding_service,
            chroma_client=chroma_client,
            similarity_threshold=0.3,  # Lower threshold for partial matches
            confidence_threshold=0.6,
            top_k=5,
        )
        
        # Store the content
        metadata = {
            "document_id": "test_doc",
            "chunk_index": 0,
            "grade": grade,
            "syllabus": syllabus.value,
            "subject": subject,
            "chapter": "Test Chapter",
        }
        self._store_content(chroma_client, embedding_service, content, metadata)
        
        # Query with first half of the content
        query = content[:len(content)//2]
        assume(len(query.strip()) >= 30)
        
        chunks = rag_engine.retrieve_chunks(query)
        
        # Property: Should retrieve chunks when querying with partial content
        assert len(chunks) > 0, "Should retrieve at least one chunk"
        
        # Partial content should still have reasonable similarity
        best_chunk = chunks[0]
        assert best_chunk.similarity > 0, (
            f"Best chunk should have positive similarity, got {best_chunk.similarity}"
        )

    @given(
        content=educational_content_strategy,
        unrelated_query=st.text(
            alphabet=st.characters(whitelist_categories=("L", "N", "Zs")),
            min_size=20,
            max_size=100,
        ).filter(lambda x: len(x.strip()) >= 20),
        grade=grade_strategy,
        syllabus=syllabus_strategy,
        subject=subject_strategy,
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_rag_retrieval_filters_by_threshold(
        self,
        content: str,
        unrelated_query: str,
        grade: int,
        syllabus: Syllabus,
        subject: str,
    ):
        """
        Feature: autism-science-tutor, Property 2: RAG Retrieval Relevance
        Validates: Requirements 1.2
        
        For any query, the RAG engine should filter chunks by the configured
        similarity threshold, ensuring only relevant content is returned.
        """
        assume(len(content.strip()) >= 50)
        assume(any(c.isalnum() for c in content))
        assume(len(unrelated_query.strip()) >= 20)
        
        # Create fresh mock services
        embedding_service = MockEmbeddingService()
        chroma_client = MockChromaDBClient()
        
        similarity_threshold = 0.5
        rag_engine = RAGEngine(
            embedding_service=embedding_service,
            chroma_client=chroma_client,
            similarity_threshold=similarity_threshold,
            confidence_threshold=0.6,
            top_k=5,
        )
        
        # Store the content
        metadata = {
            "document_id": "test_doc",
            "chunk_index": 0,
            "grade": grade,
            "syllabus": syllabus.value,
            "subject": subject,
            "chapter": "Test Chapter",
        }
        self._store_content(chroma_client, embedding_service, content, metadata)
        
        # Query and filter by threshold
        chunks = rag_engine.retrieve_chunks(unrelated_query)
        filtered_chunks = rag_engine._filter_by_similarity_threshold(chunks)
        
        # Property: All filtered chunks should be above threshold
        for chunk in filtered_chunks:
            assert chunk.similarity >= similarity_threshold, (
                f"Filtered chunk similarity {chunk.similarity} should be >= "
                f"threshold {similarity_threshold}"
            )

    @given(
        contents=st.lists(
            educational_content_strategy,
            min_size=2,
            max_size=5,
        ),
        grade=grade_strategy,
        syllabus=syllabus_strategy,
        subject=subject_strategy,
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_rag_retrieval_ranks_by_similarity(
        self,
        contents: list[str],
        grade: int,
        syllabus: Syllabus,
        subject: str,
    ):
        """
        Feature: autism-science-tutor, Property 2: RAG Retrieval Relevance
        Validates: Requirements 1.2
        
        For any set of stored content, retrieved chunks should be ranked
        by similarity score in descending order.
        """
        # Filter valid contents
        valid_contents = [c for c in contents if len(c.strip()) >= 50 and any(ch.isalnum() for ch in c)]
        assume(len(valid_contents) >= 2)
        
        # Create fresh mock services
        embedding_service = MockEmbeddingService()
        chroma_client = MockChromaDBClient()
        
        rag_engine = RAGEngine(
            embedding_service=embedding_service,
            chroma_client=chroma_client,
            similarity_threshold=0.0,  # No threshold to get all results
            confidence_threshold=0.6,
            top_k=10,
        )
        
        # Store multiple contents
        for i, content in enumerate(valid_contents):
            metadata = {
                "document_id": f"test_doc_{i}",
                "chunk_index": 0,
                "grade": grade,
                "syllabus": syllabus.value,
                "subject": subject,
                "chapter": "Test Chapter",
            }
            embedding = embedding_service.embed_single(content)
            chroma_client.add_documents(
                ids=[f"test_doc_{i}_chunk_0"],
                embeddings=[embedding],
                documents=[content],
                metadatas=[metadata],
            )
        
        # Query with first content
        query = valid_contents[0]
        chunks = rag_engine.retrieve_chunks(query)
        
        # Property: Chunks should be sorted by similarity (descending)
        assert len(chunks) > 0, "Should retrieve at least one chunk"
        
        for i in range(len(chunks) - 1):
            assert chunks[i].similarity >= chunks[i + 1].similarity, (
                f"Chunks should be sorted by similarity: "
                f"{chunks[i].similarity} >= {chunks[i + 1].similarity}"
            )
