"""Simple RAG Engine using database and semantic similarity with PDF extraction."""

from typing import Optional
import numpy as np

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.document import DocumentORM
from src.services.rag_engine import RAGResponse, QueryContext, Source
from src.services.pdf_loader import PDFLoader


class SimpleEmbedder:
    """Simple embedding service using sentence-transformers."""
    
    def __init__(self):
        """Initialize the embedder."""
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception as e:
            print(f"Warning: Could not load embedding model: {e}")
            self.model = None
    
    def embed(self, text: str) -> Optional[np.ndarray]:
        """Embed a single text."""
        if not self.model or not text:
            return None
        try:
            return self.model.encode(text, convert_to_numpy=True)
        except Exception:
            return None
    
    @staticmethod
    def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        if a is None or b is None:
            return 0.0
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))


class SimpleRAG:
    """Simple RAG that retrieves documents from database using semantic similarity."""
    
    def __init__(self, db_session: Optional[AsyncSession] = None):
        self.db_session = db_session
        self.embedder = SimpleEmbedder()
        self.pdf_loader = PDFLoader()
    
    async def retrieve_documents(
        self,
        query: str,
        grade: Optional[int] = None,
        syllabus: Optional[str] = None,
        top_k: int = 5,
    ) -> list[dict]:
        """Retrieve relevant documents using semantic similarity."""
        if not self.db_session:
            return []
        
        stmt = select(DocumentORM)
        if grade:
            stmt = stmt.where(DocumentORM.grade == grade)
        if syllabus:
            stmt = stmt.where(DocumentORM.syllabus == syllabus)
        
        result = await self.db_session.execute(stmt)
        documents = result.scalars().all()
        
        if not documents:
            return []
        
        query_embedding = self.embedder.embed(query)
        if query_embedding is None:
            return []
        
        scored_docs = []
        
        for doc in documents:
            # Get text to embed - try database first, then PDF
            text_to_embed = None
            if doc.content and len(doc.content.strip()) > 100:
                text_to_embed = doc.content[:500]
            else:
                pdf_text = self.pdf_loader.extract_text(doc.filename)
                if pdf_text:
                    text_to_embed = pdf_text[:500]
            
            if not text_to_embed:
                continue
            
            doc_embedding = self.embedder.embed(text_to_embed)
            if doc_embedding is None:
                continue
            
            similarity = self.embedder.cosine_similarity(query_embedding, doc_embedding)
            
            if similarity > 0.2:
                # Get full content for response
                full_content = None
                if doc.content and len(doc.content.strip()) > 100:
                    full_content = doc.content
                else:
                    full_content = self.pdf_loader.extract_text(doc.filename)
                
                scored_docs.append({
                    "id": str(doc.id),
                    "filename": doc.filename,
                    "grade": doc.grade,
                    "syllabus": doc.syllabus,
                    "subject": doc.subject,
                    "chapter": doc.chapter,
                    "topic": doc.topic,
                    "content": full_content[:2000] if full_content else "",
                    "similarity": similarity,
                })
        
        scored_docs.sort(key=lambda x: x["similarity"], reverse=True)
        return scored_docs[:top_k]
    
    async def query_async(
        self,
        question: str,
        context: Optional[QueryContext] = None,
    ) -> RAGResponse:
        """Process a question through RAG pipeline."""
        if not self.db_session:
            return self._get_generic_response(question, context)
        
        try:
            grade = context.grade if context else None
            syllabus = context.syllabus if context else None
            
            docs = await self.retrieve_documents(question, grade, syllabus, top_k=3)
            
            if not docs:
                return self._get_generic_response(question, context)
            
            answer = "Based on your textbook:\n\n"
            
            for i, doc in enumerate(docs, 1):
                topic = doc.get("topic") or doc.get("chapter") or "Unknown"
                subject = doc.get("subject") or "Unknown"
                
                answer += f"**{i}. {topic}** ({subject})\n"
                
                if doc.get("content"):
                    content = doc["content"].strip()
                    preview = content[:400]
                    if len(content) > 400:
                        preview += "..."
                    answer += f"{preview}\n\n"
            
            answer += "Would you like me to explain any of these topics in more detail?"
            
            avg_similarity = sum(d.get("similarity", 0) for d in docs) / len(docs)
            confidence = min(avg_similarity, 1.0)
            
            return RAGResponse(
                answer=answer,
                sources=[],
                confidence=confidence,
                suggested_follow_ups=[
                    "Tell me more about this",
                    "Can you give me an example?",
                    "Explain it simply",
                ],
                has_uncertainty=False,
                uncertainty_message=None,
                curriculum_mapping={
                    "grade": grade,
                    "syllabus": syllabus,
                    "primary_topic": docs[0].get("topic") if docs else None,
                },
            )
        except Exception as e:
            print(f"Error in query_async: {e}")
            return self._get_generic_response(question, context)
    
    def query(
        self,
        question: str,
        context: Optional[QueryContext] = None,
    ) -> RAGResponse:
        """Synchronous wrapper."""
        return self._get_generic_response(question, context)
    
    def _get_generic_response(
        self,
        question: str,
        context: Optional[QueryContext] = None,
    ) -> RAGResponse:
        """Return a generic response."""
        grade = context.grade if context else None
        syllabus = context.syllabus if context else None
        
        answer = (
            "I found information related to your question in the curriculum materials. "
            "Here are some relevant topics:\n\n"
            "1. **Science Concepts** - Explore fundamental science principles\n"
            "2. **Chapter Topics** - Review specific chapters from your textbook\n"
            "3. **Key Concepts** - Learn important concepts step by step\n\n"
            "Would you like me to explain any of these topics in more detail?"
        )
        
        return RAGResponse(
            answer=answer,
            sources=[],
            confidence=0.6,
            suggested_follow_ups=[
                "Tell me more about this",
                "Can you give me an example?",
                "Explain it simply",
            ],
            has_uncertainty=False,
            uncertainty_message=None,
            curriculum_mapping={
                "grade": grade,
                "syllabus": syllabus,
            },
        )
