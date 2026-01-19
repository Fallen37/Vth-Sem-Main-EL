"""RAG Engine Service - handles retrieval and generation for the AI tutor."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from config.settings import get_settings
from src.models.document import ContentFilters, CurriculumInfo
from src.models.enums import Syllabus


settings = get_settings()


class Source(BaseModel):
    """Source reference for RAG response."""

    document_id: str
    chunk_index: int
    content_preview: str = Field(description="First 200 chars of the chunk")
    similarity: float
    grade: Optional[int] = None
    syllabus: Optional[str] = None
    subject: Optional[str] = None
    chapter: Optional[str] = None
    topic: Optional[str] = None


class Chunk(BaseModel):
    """Retrieved chunk from vector database."""

    content: str
    metadata: dict
    similarity: float


class RAGResponse(BaseModel):
    """Response from RAG query."""

    answer: str
    sources: list[Source] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    suggested_follow_ups: list[str] = Field(default_factory=list)
    has_uncertainty: bool = False
    uncertainty_message: Optional[str] = None
    curriculum_mapping: Optional[dict] = None


class QueryContext(BaseModel):
    """Context for RAG query."""

    student_id: Optional[UUID] = None
    grade: Optional[int] = Field(None, ge=5, le=10)
    syllabus: Optional[Syllabus] = None
    conversation_history: list[dict] = Field(default_factory=list)
    preferred_explanation_style: Optional[dict] = None


@dataclass
class RAGEngine:
    """
    RAG Engine for retrieval-augmented generation.
    
    Handles:
    - Retrieving relevant chunks from ChromaDB
    - Generating responses using LLM
    - Uncertainty detection and handling
    - Curriculum prioritization
    """

    embedding_service: Optional[EmbeddingService] = None
    chroma_client: Optional[ChromaDBClient] = None
    llm_client: Optional[Any] = None
    
    # Configuration
    similarity_threshold: float = field(default_factory=lambda: settings.rag_similarity_threshold)
    confidence_threshold: float = field(default_factory=lambda: settings.rag_confidence_threshold)
    top_k: int = field(default_factory=lambda: settings.rag_top_k)

    def __post_init__(self):
        """Initialize services lazily."""
        pass

    @property
    def _embedding_service(self):
        """Lazy initialization of embedding service."""
        if self.embedding_service is None:
            from src.services.content_ingestion import EmbeddingService
            self.embedding_service = EmbeddingService()
        return self.embedding_service

    @property
    def _chroma_client(self):
        """Lazy initialization of ChromaDB client."""
        if self.chroma_client is None:
            from src.services.content_ingestion import ChromaDBClient
            self.chroma_client = ChromaDBClient()
        return self.chroma_client

    def _get_llm_client(self) -> Any:
        """Get or initialize LLM client."""
        if self.llm_client is None:
            try:
                from openai import OpenAI
                self.llm_client = OpenAI(api_key=settings.openai_api_key)
            except ImportError:
                raise ImportError("openai is required. Install with: pip install openai")
        return self.llm_client

    def retrieve_chunks(
        self,
        question: str,
        filters: Optional[ContentFilters] = None,
        top_k: Optional[int] = None,
    ) -> list[Chunk]:
        """
        Retrieve relevant chunks from ChromaDB.
        
        Args:
            question: The question to search for
            filters: Optional content filters (grade, syllabus, subject, etc.)
            top_k: Number of results to return (defaults to configured value)
            
        Returns:
            List of Chunk objects with content, metadata, and similarity scores
        """
        if top_k is None:
            top_k = self.top_k

        # Generate query embedding
        query_embedding = self._embedding_service.embed_single(question)

        # Build where clause from filters
        where = filters.to_chroma_filter() if filters else None

        # Query ChromaDB
        results = self._chroma_client.query(
            query_embedding=query_embedding,
            n_results=top_k,
            where=where,
        )

        # Convert results to Chunk objects
        chunks = []
        if results and results.get("documents") and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
                distance = results["distances"][0][i] if results.get("distances") else 0.0
                # Convert cosine distance to similarity (ChromaDB uses cosine distance)
                similarity = 1.0 - distance

                chunks.append(Chunk(
                    content=doc,
                    metadata=metadata,
                    similarity=similarity,
                ))

        return chunks

    def _filter_by_similarity_threshold(
        self,
        chunks: list[Chunk],
        threshold: Optional[float] = None,
    ) -> list[Chunk]:
        """Filter chunks by similarity threshold."""
        if threshold is None:
            threshold = self.similarity_threshold
        return [c for c in chunks if c.similarity >= threshold]

    def _calculate_confidence(self, chunks: list[Chunk]) -> float:
        """
        Calculate confidence score based on retrieved chunks.
        
        Confidence is based on:
        - Number of relevant chunks found
        - Average similarity of top chunks
        - Consistency of information across chunks
        """
        if not chunks:
            return 0.0

        # Get chunks above threshold
        relevant_chunks = self._filter_by_similarity_threshold(chunks)
        
        if not relevant_chunks:
            return 0.0

        # Calculate average similarity of relevant chunks
        avg_similarity = sum(c.similarity for c in relevant_chunks) / len(relevant_chunks)
        
        # Factor in number of relevant chunks (more sources = higher confidence)
        chunk_factor = min(len(relevant_chunks) / 3, 1.0)  # Cap at 3 chunks
        
        # Combined confidence score
        confidence = avg_similarity * 0.7 + chunk_factor * 0.3
        
        return min(confidence, 1.0)

    def _build_context(self, chunks: list[Chunk]) -> str:
        """Build context string from retrieved chunks."""
        if not chunks:
            return ""
        
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            source_info = []
            if chunk.metadata.get("subject"):
                source_info.append(f"Subject: {chunk.metadata['subject']}")
            if chunk.metadata.get("chapter"):
                source_info.append(f"Chapter: {chunk.metadata['chapter']}")
            if chunk.metadata.get("topic"):
                source_info.append(f"Topic: {chunk.metadata['topic']}")
            
            source_str = f" ({', '.join(source_info)})" if source_info else ""
            context_parts.append(f"[Source {i}{source_str}]\n{chunk.content}")
        
        return "\n\n".join(context_parts)

    def _build_sources(self, chunks: list[Chunk]) -> list[Source]:
        """Build source references from chunks."""
        sources = []
        for chunk in chunks:
            sources.append(Source(
                document_id=chunk.metadata.get("document_id", "unknown"),
                chunk_index=chunk.metadata.get("chunk_index", 0),
                content_preview=chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content,
                similarity=chunk.similarity,
                grade=chunk.metadata.get("grade"),
                syllabus=chunk.metadata.get("syllabus"),
                subject=chunk.metadata.get("subject"),
                chapter=chunk.metadata.get("chapter"),
                topic=chunk.metadata.get("topic"),
            ))
        return sources

    def _generate_uncertainty_message(self, question: str, confidence: float) -> str:
        """Generate an appropriate uncertainty message."""
        if confidence < 0.3:
            return (
                "I don't have enough information in my knowledge base to answer this question confidently. "
                "Could you try rephrasing your question, or ask about a specific topic from your textbook?"
            )
        elif confidence < self.confidence_threshold:
            return (
                "I found some related information, but I'm not entirely sure it answers your question. "
                "Let me share what I found, but please verify with your textbook or teacher."
            )
        return ""

    def _generate_follow_ups(self, question: str, chunks: list[Chunk]) -> list[str]:
        """Generate suggested follow-up questions based on context."""
        follow_ups = []
        
        # Extract topics from chunks for follow-up suggestions
        topics = set()
        chapters = set()
        for chunk in chunks:
            if chunk.metadata.get("topic"):
                topics.add(chunk.metadata["topic"])
            if chunk.metadata.get("chapter"):
                chapters.add(chunk.metadata["chapter"])
        
        if topics:
            topic = list(topics)[0]
            follow_ups.append(f"Can you explain more about {topic}?")
            follow_ups.append(f"What are the key points of {topic}?")
        
        if chapters:
            chapter = list(chapters)[0]
            follow_ups.append(f"What else should I know about {chapter}?")
        
        # Add generic follow-ups
        follow_ups.extend([
            "Can you give me an example?",
            "Can you explain this in simpler words?",
        ])
        
        return follow_ups[:5]  # Limit to 5 suggestions

    def _build_curriculum_mapping(self, chunks: list[Chunk]) -> Optional[dict]:
        """Build curriculum mapping from retrieved chunks."""
        if not chunks:
            return None
        
        # Get the most relevant chunk's curriculum info
        best_chunk = chunks[0]
        mapping = {}
        
        if best_chunk.metadata.get("grade"):
            mapping["grade"] = best_chunk.metadata["grade"]
        if best_chunk.metadata.get("syllabus"):
            mapping["syllabus"] = best_chunk.metadata["syllabus"]
        if best_chunk.metadata.get("subject"):
            mapping["subject"] = best_chunk.metadata["subject"]
        if best_chunk.metadata.get("chapter"):
            mapping["chapter"] = best_chunk.metadata["chapter"]
        if best_chunk.metadata.get("topic"):
            mapping["topic"] = best_chunk.metadata["topic"]
        
        return mapping if mapping else None

    def _generate_with_llm(
        self,
        question: str,
        context: str,
        query_context: Optional[QueryContext] = None,
    ) -> str:
        """Generate answer using LLM."""
        client = self._get_llm_client()
        
        # Build system prompt
        system_prompt = """You are a friendly science tutor helping autistic students aged 10-16 learn science.

Guidelines:
- Use clear, simple language appropriate for the student's grade level
- Break down complex concepts into smaller, manageable parts
- Use examples and analogies when helpful
- Be patient and encouraging
- If the context doesn't contain enough information, say so honestly
- Always base your answers on the provided context

"""
        
        if query_context and query_context.preferred_explanation_style:
            style = query_context.preferred_explanation_style
            if style.get("use_examples"):
                system_prompt += "- Include practical examples\n"
            if style.get("use_diagrams"):
                system_prompt += "- Describe visual representations when helpful\n"
            if style.get("step_by_step"):
                system_prompt += "- Explain step by step\n"
            if style.get("simplify_language"):
                system_prompt += "- Use very simple words\n"

        # Build user prompt
        user_prompt = f"""Based on the following educational content, please answer the student's question.

Context:
{context}

Student's Question: {question}

Please provide a helpful, accurate answer based on the context above."""

        try:
            response = client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=1000,
            )
            return response.choices[0].message.content
        except Exception as e:
            # Return a fallback response if LLM fails
            return f"I encountered an issue generating a response. Here's what I found in your curriculum materials:\n\n{context[:500]}..."

    def query(
        self,
        question: str,
        context: Optional[QueryContext] = None,
    ) -> RAGResponse:
        """
        Process a question through the RAG pipeline.
        
        Args:
            question: The student's question
            context: Optional query context with student info and preferences
            
        Returns:
            RAGResponse with answer, sources, confidence, and follow-ups
        """
        # Build filters from context
        filters = None
        if context and (context.grade or context.syllabus):
            filters = ContentFilters(
                grade=context.grade,
                syllabus=context.syllabus,
            )

        # Retrieve relevant chunks
        chunks = self.retrieve_chunks(question, filters=filters)
        
        # Filter by similarity threshold
        relevant_chunks = self._filter_by_similarity_threshold(chunks)
        
        # Calculate confidence
        confidence = self._calculate_confidence(chunks)
        
        # Check for uncertainty
        has_uncertainty = confidence < self.confidence_threshold
        uncertainty_message = None
        
        if has_uncertainty:
            uncertainty_message = self._generate_uncertainty_message(question, confidence)
        
        # Build context for LLM
        llm_context = self._build_context(relevant_chunks)
        
        # Generate answer
        if relevant_chunks:
            answer = self._generate_with_llm(question, llm_context, context)
            if has_uncertainty and uncertainty_message:
                answer = f"{uncertainty_message}\n\n{answer}"
        else:
            answer = self._generate_uncertainty_message(question, 0.0)
            has_uncertainty = True
        
        # Build response
        return RAGResponse(
            answer=answer,
            sources=self._build_sources(relevant_chunks),
            confidence=confidence,
            suggested_follow_ups=self._generate_follow_ups(question, relevant_chunks),
            has_uncertainty=has_uncertainty,
            uncertainty_message=uncertainty_message,
            curriculum_mapping=self._build_curriculum_mapping(relevant_chunks),
        )


    def retrieve_with_curriculum_priority(
        self,
        question: str,
        student_curriculum: CurriculumInfo,
        top_k: Optional[int] = None,
    ) -> list[Chunk]:
        """
        Retrieve chunks with curriculum-based prioritization.
        
        Chunks matching the student's grade and syllabus are boosted in ranking.
        
        Args:
            question: The question to search for
            student_curriculum: Student's curriculum info (grade, syllabus, subject, etc.)
            top_k: Number of results to return
            
        Returns:
            List of Chunk objects, prioritized by curriculum match
        """
        if top_k is None:
            top_k = self.top_k

        # First, try to get chunks matching the exact curriculum
        exact_filters = ContentFilters(
            grade=student_curriculum.grade,
            syllabus=student_curriculum.syllabus,
        )
        
        # Add subject filter if available
        if student_curriculum.subject:
            exact_filters.subject = student_curriculum.subject
        
        exact_chunks = self.retrieve_chunks(question, filters=exact_filters, top_k=top_k)
        
        # If we have enough exact matches, return them
        if len(exact_chunks) >= top_k:
            return self._apply_curriculum_boost(exact_chunks, student_curriculum)
        
        # Otherwise, get more chunks without strict filtering
        all_chunks = self.retrieve_chunks(question, filters=None, top_k=top_k * 2)
        
        # Apply curriculum boost and re-rank
        boosted_chunks = self._apply_curriculum_boost(all_chunks, student_curriculum)
        
        # Sort by boosted similarity
        boosted_chunks.sort(key=lambda c: c.similarity, reverse=True)
        
        return boosted_chunks[:top_k]

    def _apply_curriculum_boost(
        self,
        chunks: list[Chunk],
        student_curriculum: CurriculumInfo,
    ) -> list[Chunk]:
        """
        Apply curriculum-based boost to chunk similarity scores.
        
        Boost factors:
        - Exact grade match: +0.15
        - Exact syllabus match: +0.10
        - Subject match: +0.05
        - Chapter match: +0.05
        - Topic match: +0.05
        """
        boosted_chunks = []
        
        for chunk in chunks:
            boost = 0.0
            
            # Grade match boost
            chunk_grade = chunk.metadata.get("grade")
            if chunk_grade and chunk_grade == student_curriculum.grade:
                boost += 0.15
            
            # Syllabus match boost
            chunk_syllabus = chunk.metadata.get("syllabus")
            if chunk_syllabus and chunk_syllabus == student_curriculum.syllabus.value:
                boost += 0.10
            
            # Subject match boost
            chunk_subject = chunk.metadata.get("subject", "").lower()
            if student_curriculum.subject and chunk_subject == student_curriculum.subject.lower():
                boost += 0.05
            
            # Chapter match boost
            chunk_chapter = chunk.metadata.get("chapter", "").lower()
            if student_curriculum.chapter and chunk_chapter == student_curriculum.chapter.lower():
                boost += 0.05
            
            # Topic match boost
            chunk_topic = chunk.metadata.get("topic", "").lower()
            if student_curriculum.topic and chunk_topic == student_curriculum.topic.lower():
                boost += 0.05
            
            # Create new chunk with boosted similarity (capped at 1.0)
            boosted_similarity = min(chunk.similarity + boost, 1.0)
            boosted_chunks.append(Chunk(
                content=chunk.content,
                metadata=chunk.metadata,
                similarity=boosted_similarity,
            ))
        
        return boosted_chunks

    def map_question_to_curriculum(
        self,
        question: str,
        student_curriculum: Optional[CurriculumInfo] = None,
    ) -> dict:
        """
        Map a question to curriculum chapters and topics.
        
        Args:
            question: The student's question
            student_curriculum: Optional curriculum context for filtering
            
        Returns:
            Dictionary with mapped curriculum information
        """
        # Build filters if curriculum context provided
        filters = None
        if student_curriculum:
            filters = ContentFilters(
                grade=student_curriculum.grade,
                syllabus=student_curriculum.syllabus,
            )
        
        # Retrieve relevant chunks
        chunks = self.retrieve_chunks(question, filters=filters, top_k=10)
        
        if not chunks:
            return {
                "mapped": False,
                "chapters": [],
                "topics": [],
                "subjects": [],
            }
        
        # Extract curriculum info from chunks
        chapters = {}
        topics = {}
        subjects = {}
        
        for chunk in chunks:
            # Only consider chunks above threshold
            if chunk.similarity < self.similarity_threshold:
                continue
            
            chapter = chunk.metadata.get("chapter")
            topic = chunk.metadata.get("topic")
            subject = chunk.metadata.get("subject")
            
            if chapter:
                if chapter not in chapters:
                    chapters[chapter] = {"count": 0, "max_similarity": 0}
                chapters[chapter]["count"] += 1
                chapters[chapter]["max_similarity"] = max(
                    chapters[chapter]["max_similarity"],
                    chunk.similarity
                )
            
            if topic:
                if topic not in topics:
                    topics[topic] = {"count": 0, "max_similarity": 0}
                topics[topic]["count"] += 1
                topics[topic]["max_similarity"] = max(
                    topics[topic]["max_similarity"],
                    chunk.similarity
                )
            
            if subject:
                if subject not in subjects:
                    subjects[subject] = {"count": 0, "max_similarity": 0}
                subjects[subject]["count"] += 1
                subjects[subject]["max_similarity"] = max(
                    subjects[subject]["max_similarity"],
                    chunk.similarity
                )
        
        # Sort by relevance (count * similarity)
        def sort_key(item):
            return item[1]["count"] * item[1]["max_similarity"]
        
        sorted_chapters = sorted(chapters.items(), key=sort_key, reverse=True)
        sorted_topics = sorted(topics.items(), key=sort_key, reverse=True)
        sorted_subjects = sorted(subjects.items(), key=sort_key, reverse=True)
        
        return {
            "mapped": bool(chapters or topics),
            "chapters": [
                {"name": name, "relevance": data["max_similarity"]}
                for name, data in sorted_chapters[:5]
            ],
            "topics": [
                {"name": name, "relevance": data["max_similarity"]}
                for name, data in sorted_topics[:5]
            ],
            "subjects": [
                {"name": name, "relevance": data["max_similarity"]}
                for name, data in sorted_subjects[:3]
            ],
            "primary_chapter": sorted_chapters[0][0] if sorted_chapters else None,
            "primary_topic": sorted_topics[0][0] if sorted_topics else None,
            "primary_subject": sorted_subjects[0][0] if sorted_subjects else None,
        }

    def query_with_curriculum_priority(
        self,
        question: str,
        student_curriculum: CurriculumInfo,
        context: Optional[QueryContext] = None,
    ) -> RAGResponse:
        """
        Process a question with curriculum prioritization.
        
        This method:
        1. Retrieves chunks with curriculum-based boosting
        2. Maps the question to curriculum chapters/topics
        3. Generates a response with source references
        
        Args:
            question: The student's question
            student_curriculum: Student's curriculum info
            context: Optional additional query context
            
        Returns:
            RAGResponse with curriculum-prioritized answer and mapping
        """
        # Retrieve with curriculum priority
        chunks = self.retrieve_with_curriculum_priority(
            question,
            student_curriculum,
        )
        
        # Filter by similarity threshold
        relevant_chunks = self._filter_by_similarity_threshold(chunks)
        
        # Calculate confidence
        confidence = self._calculate_confidence(chunks)
        
        # Check for uncertainty
        has_uncertainty = confidence < self.confidence_threshold
        uncertainty_message = None
        
        if has_uncertainty:
            uncertainty_message = self._generate_uncertainty_message(question, confidence)
        
        # Map question to curriculum
        curriculum_mapping = self.map_question_to_curriculum(question, student_curriculum)
        
        # Build context for LLM
        llm_context = self._build_context(relevant_chunks)
        
        # Generate answer
        if relevant_chunks:
            answer = self._generate_with_llm(question, llm_context, context)
            if has_uncertainty and uncertainty_message:
                answer = f"{uncertainty_message}\n\n{answer}"
        else:
            answer = self._generate_uncertainty_message(question, 0.0)
            has_uncertainty = True
        
        # Build response with curriculum info
        return RAGResponse(
            answer=answer,
            sources=self._build_sources(relevant_chunks),
            confidence=confidence,
            suggested_follow_ups=self._generate_follow_ups(question, relevant_chunks),
            has_uncertainty=has_uncertainty,
            uncertainty_message=uncertainty_message,
            curriculum_mapping=curriculum_mapping,
        )
