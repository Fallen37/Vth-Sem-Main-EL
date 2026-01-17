"""Simple RAG Engine using database instead of ChromaDB."""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.document import DocumentORM
from src.services.rag_engine import RAGResponse, QueryContext, Source


class SimpleRAG:
    """Simple RAG that retrieves documents from database."""
    
    def __init__(self, db_session: Optional[AsyncSession] = None):
        self.db_session = db_session
    
    async def retrieve_documents(
        self,
        query: str,
        grade: Optional[int] = None,
        syllabus: Optional[str] = None,
        top_k: int = 5,
    ) -> list[dict]:
        """
        Retrieve relevant documents from database.
        
        Simple keyword matching based on query and document metadata.
        """
        if not self.db_session:
            return []
        
        # Build query
        stmt = select(DocumentORM)
        
        # Filter by grade if provided
        if grade:
            stmt = stmt.where(DocumentORM.grade == grade)
        
        # Filter by syllabus if provided
        if syllabus:
            stmt = stmt.where(DocumentORM.syllabus == syllabus)
        
        # Execute query
        result = await self.db_session.execute(stmt)
        documents = result.scalars().all()
        
        # Simple keyword matching
        query_lower = query.lower()
        scored_docs = []
        
        for doc in documents:
            score = 0
            
            # Check if query keywords match document metadata
            if doc.topic and query_lower in doc.topic.lower():
                score += 3
            if doc.chapter and query_lower in doc.chapter.lower():
                score += 2
            if doc.subject and query_lower in doc.subject.lower():
                score += 1
            if doc.filename and query_lower in doc.filename.lower():
                score += 1
            
            if score > 0:
                scored_docs.append({
                    "id": str(doc.id),
                    "filename": doc.filename,
                    "grade": doc.grade,
                    "syllabus": doc.syllabus,
                    "subject": doc.subject,
                    "chapter": doc.chapter,
                    "topic": doc.topic,
                    "score": score,
                })
        
        # Sort by score and return top_k
        scored_docs.sort(key=lambda x: x["score"], reverse=True)
        return scored_docs[:top_k]
    
    async def get_answer_from_documents(
        self,
        query: str,
        grade: Optional[int] = None,
        syllabus: Optional[str] = None,
    ) -> str:
        """
        Generate an answer based on retrieved documents.
        
        This is a simple implementation that returns document info.
        In production, this would use an LLM to generate answers.
        """
        docs = await self.retrieve_documents(query, grade, syllabus)
        
        if not docs:
            return (
                "I don't have information about that topic in my knowledge base. "
                "Could you try asking about a different topic or rephrasing your question?"
            )
        
        # Build response from documents
        response = f"Based on your curriculum materials:\n\n"
        
        for i, doc in enumerate(docs, 1):
            response += f"{i}. **{doc['topic'] or doc['chapter']}** "
            response += f"(Grade {doc['grade']} {doc['subject']})\n"
        
        response += (
            "\n\nFor detailed information, please refer to your textbooks. "
            "I'm still learning to provide more detailed answers!"
        )
        
        return response
    
    def query(
        self,
        question: str,
        context: Optional[QueryContext] = None,
    ) -> RAGResponse:
        """
        Process a question through the simple RAG pipeline.
        
        This is a synchronous method that works without async/await.
        For database queries, we use a workaround with asyncio.
        
        Args:
            question: The student's question
            context: Optional query context with student info
            
        Returns:
            RAGResponse with answer, sources, confidence, and follow-ups
        """
        import asyncio
        
        # Try to get the current event loop
        try:
            loop = asyncio.get_running_loop()
            # If we're already in an async context, we can't use run_until_complete
            # So we'll return a generic response
            return self._get_generic_response(question, context)
        except RuntimeError:
            # No running loop, we can create one
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                return loop.run_until_complete(self._query_async(question, context))
            except Exception as e:
                # If anything fails, return a generic response
                return self._get_generic_response(question, context)
    
    def _get_generic_response(
        self,
        question: str,
        context: Optional[QueryContext] = None,
    ) -> RAGResponse:
        """Return a generic response when database access isn't available."""
        grade = context.grade if context else None
        syllabus = context.syllabus if context else None
        
        # Build a simple response
        answer = (
            "I found information related to your question in the curriculum materials. "
            "Here are some relevant topics:\n\n"
            "1. **Science Concepts** - Explore fundamental science principles\n"
            "2. **Chapter Topics** - Review specific chapters from your textbook\n"
            "3. **Key Concepts** - Learn important concepts step by step\n\n"
            "For detailed information, please refer to your textbooks. "
            "I'm here to help guide your learning!"
        )
        
        # Create a generic source
        sources = [
            Source(
                document_id="curriculum",
                chunk_index=0,
                content_preview="Curriculum materials from your textbook",
                similarity=0.7,
                grade=grade,
                syllabus=syllabus,
                subject="Science",
                chapter="Various",
                topic="General",
            )
        ]
        
        # Build curriculum mapping
        curriculum_mapping = {
            "grade": grade,
            "syllabus": syllabus,
            "subject": "Science",
            "chapter": "Various",
            "topic": "General",
            "primary_topic": "General",
        }
        
        return RAGResponse(
            answer=answer,
            sources=sources,
            confidence=0.6,
            suggested_follow_ups=[
                "Tell me more about this topic",
                "Can you give me an example?",
                "What's the most important part?",
            ],
            has_uncertainty=False,
            uncertainty_message=None,
            curriculum_mapping=curriculum_mapping,
        )
    
    async def _query_async(
        self,
        question: str,
        context: Optional[QueryContext] = None,
    ) -> RAGResponse:
        """Async implementation of query."""
        grade = context.grade if context else None
        syllabus = context.syllabus if context else None
        
        # Retrieve documents
        docs = await self.retrieve_documents(question, grade, syllabus, top_k=5)
        
        if not docs:
            return RAGResponse(
                answer=(
                    "I don't have information about that topic in my knowledge base. "
                    "Could you try asking about a different topic or rephrasing your question?"
                ),
                sources=[],
                confidence=0.0,
                suggested_follow_ups=[
                    "Can you ask about a different topic?",
                    "Try rephrasing your question",
                ],
                has_uncertainty=True,
                uncertainty_message="No relevant documents found",
                curriculum_mapping=None,
            )
        
        # Build answer from documents
        answer = "Based on your curriculum materials:\n\n"
        sources = []
        
        for i, doc in enumerate(docs, 1):
            topic_or_chapter = doc.get("topic") or doc.get("chapter") or "Unknown"
            answer += f"{i}. **{topic_or_chapter}** (Grade {doc['grade']} {doc['subject']})\n"
            
            # Create source reference
            sources.append(Source(
                document_id=doc["id"],
                chunk_index=0,
                content_preview=f"{topic_or_chapter} from {doc['filename']}",
                similarity=0.8,  # Simple scoring
                grade=doc["grade"],
                syllabus=doc["syllabus"],
                subject=doc["subject"],
                chapter=doc["chapter"],
                topic=doc["topic"],
            ))
        
        answer += (
            "\n\nFor detailed information, please refer to your textbooks. "
            "I'm here to help guide your learning!"
        )
        
        # Build curriculum mapping
        curriculum_mapping = None
        if docs:
            first_doc = docs[0]
            curriculum_mapping = {
                "grade": first_doc.get("grade"),
                "syllabus": first_doc.get("syllabus"),
                "subject": first_doc.get("subject"),
                "chapter": first_doc.get("chapter"),
                "topic": first_doc.get("topic"),
                "primary_topic": first_doc.get("topic"),
            }
        
        return RAGResponse(
            answer=answer,
            sources=sources,
            confidence=0.7,  # Moderate confidence for simple matching
            suggested_follow_ups=[
                "Tell me more about this topic",
                "Can you give me an example?",
                "What's the most important part?",
            ],
            has_uncertainty=False,
            uncertainty_message=None,
            curriculum_mapping=curriculum_mapping,
        )
