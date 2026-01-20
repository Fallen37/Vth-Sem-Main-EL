"""Main RAG service that orchestrates retrieval and generation."""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.pdf_loader import PDFLoader
from src.services.embeddings import EmbeddingsService
from src.services.vector_store import VectorStore
from src.services.llm_service import LLMService


class RAGService:
    """Main RAG service for retrieval-augmented generation."""
    
    def __init__(self, db_session: Optional[AsyncSession] = None):
        self.db_session = db_session
        self.pdf_loader = PDFLoader()
        self.embeddings = EmbeddingsService()
        self.vector_store = VectorStore()
        self.llm = LLMService()
        self.chat_history = []
    
    async def ingest_documents(self, documents: list[dict]) -> dict:
        """
        Ingest documents into the vector store.
        
        Args:
            documents: List of dicts with 'filename', 'content', 'metadata'
        
        Returns:
            Dict with ingestion stats
        """
        total_chunks = 0
        total_documents = 0
        
        for doc in documents:
            filename = doc.get('filename')
            metadata = doc.get('metadata', {})
            
            # Extract text from PDF
            text = self.pdf_loader.extract_text(filename)
            if not text:
                print(f"Could not extract text from {filename}")
                continue
            
            # Split into chunks
            chunks = self.pdf_loader.chunk_text(text, chunk_size=500, overlap=100)
            if not chunks:
                continue
            
            # Generate embeddings
            embeddings = self.embeddings.embed_batch(chunks)
            embeddings = [e for e in embeddings if e is not None]
            
            if len(embeddings) != len(chunks):
                print(f"Embedding mismatch for {filename}")
                continue
            
            # Add to vector store
            chunk_ids = self.vector_store.add_chunks(chunks, embeddings, metadata)
            
            total_chunks += len(chunk_ids)
            total_documents += 1
            
            print(f"Ingested {filename}: {len(chunk_ids)} chunks")
        
        return {
            'total_documents': total_documents,
            'total_chunks': total_chunks,
        }
    
    async def retrieve_context(
        self,
        query: str,
        grade: Optional[int] = None,
        top_k: int = 5,
    ) -> list[dict]:
        """
        Retrieve relevant chunks from the vector store.
        
        Args:
            query: The user's question
            grade: Optional grade filter
            top_k: Number of chunks to retrieve
        
        Returns:
            List of relevant chunks with metadata
        """
        # Embed the query
        query_embedding = self.embeddings.embed_text(query)
        if query_embedding is None:
            return []
        
        # Search vector store
        results = self.vector_store.search(query_embedding, top_k=top_k)
        
        # Filter by grade if provided
        if grade:
            results = [r for r in results if r['metadata'].get('grade') == grade]
        
        return results
    
    async def generate_response(
        self,
        query: str,
        retrieved_chunks: list[dict],
        grade: Optional[int] = None,
        system_prompt: Optional[str] = None,
    ) -> dict:
        """
        Generate a response using the LLM with retrieved context.
        
        Args:
            query: The user's question
            retrieved_chunks: Chunks retrieved from vector store
            grade: Optional grade level for context
            system_prompt: Optional custom system prompt
        
        Returns:
            Dict with response, sources, and metadata
        """
        # Build context from retrieved chunks - use more chunks for comprehensive explanation
        context = "\n\n".join([
            f"From {chunk['metadata'].get('chapter', 'Unknown')}:\n{chunk['chunk']}"
            for chunk in retrieved_chunks[:8]  # Use top 8 chunks for more comprehensive context
        ])
        
        if not context:
            context = "No relevant textbook content found for this question."
        
        # Add to chat history
        self.chat_history.append({
            "role": "user",
            "content": query
        })
        
        # Generate response
        response_text = self.llm.generate_response(
            query=query,
            context=context,
            chat_history=self.chat_history,
            system_prompt=system_prompt,
        )
        
        # Add response to chat history
        self.chat_history.append({
            "role": "assistant",
            "content": response_text
        })
        
        # Generate follow-up suggestions
        suggestions = self.llm.generate_follow_up_suggestions(response_text)
        
        return {
            'response': response_text,
            'sources': [
                {
                    'chapter': chunk['metadata'].get('chapter'),
                    'subject': chunk['metadata'].get('subject'),
                    'similarity': chunk['similarity'],
                }
                for chunk in retrieved_chunks[:8]
            ],
            'suggestions': suggestions,
            'confidence': sum(c['similarity'] for c in retrieved_chunks[:8]) / len(retrieved_chunks[:8]) if retrieved_chunks else 0,
        }
    
    async def chat(
        self,
        query: str,
        grade: Optional[int] = None,
        system_prompt: Optional[str] = None,
    ) -> dict:
        """
        Full chat pipeline: retrieve -> generate.
        
        Args:
            query: The user's question
            grade: Optional grade level
            system_prompt: Optional custom system prompt
        
        Returns:
            Dict with response and metadata
        """
        # Retrieve more relevant chunks for comprehensive explanation
        retrieved_chunks = await self.retrieve_context(query, grade=grade, top_k=10)
        
        # Generate response
        result = await self.generate_response(
            query=query,
            retrieved_chunks=retrieved_chunks,
            grade=grade,
            system_prompt=system_prompt,
        )
        
        return result
    
    def clear_history(self):
        """Clear chat history."""
        self.chat_history = []
    
    def get_history(self) -> list[dict]:
        """Get chat history."""
        return self.chat_history
