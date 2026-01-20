"""Service for analyzing and storing AI responses."""

from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.text_analyzer import get_text_analyzer
from src.models.analyzed_response import AnalyzedResponseORM


class ResponseAnalyzerService:
    """Service for analyzing AI responses and storing results."""
    
    def __init__(self, db_session: Optional[AsyncSession] = None):
        """Initialize the service."""
        self.db_session = db_session
        self.analyzer = get_text_analyzer()
    
    async def analyze_and_store(
        self,
        response_text: str,
        session_id: UUID,
        user_id: UUID,
        topic: Optional[str] = None,
    ) -> dict:
        """
        Analyze AI response and store results.
        
        Args:
            response_text: Raw AI response
            session_id: Session ID
            user_id: User ID
            topic: Topic being discussed
        
        Returns:
            Dict with analysis results and content_text for frontend
        """
        # Analyze the response
        analysis = self.analyzer.analyze(
            response_text=response_text,
            session_id=session_id,
            topic=topic,
        )
        
        # Store in database if session available
        if self.db_session:
            await self._store_analysis(
                analysis=analysis,
                session_id=session_id,
                user_id=user_id,
                original_response=response_text,
            )
        
        return analysis
    
    async def _store_analysis(
        self,
        analysis: dict,
        session_id: UUID,
        user_id: UUID,
        original_response: str,
    ) -> None:
        """Store analysis results in database."""
        try:
            record = AnalyzedResponseORM(
                session_id=str(session_id),
                user_id=str(user_id),
                topic=analysis.get("topic"),
                original_response=original_response,
                meta_text=analysis.get("meta_text"),
                content_text=analysis.get("content_text"),
                analysis_method=analysis.get("analysis_method", "rule-based"),
                meta_sentence_count=analysis.get("meta_sentence_count", 0),
                content_sentence_count=analysis.get("content_sentence_count", 0),
            )
            
            self.db_session.add(record)
            await self.db_session.commit()
        except Exception as e:
            print(f"Error storing analysis: {e}")
            # Don't fail the request if storage fails
            pass
    
    async def get_analysis_history(
        self,
        session_id: UUID,
        limit: int = 10,
    ) -> list:
        """Get analysis history for a session."""
        if not self.db_session:
            return []
        
        try:
            from sqlalchemy import select, desc
            
            stmt = select(AnalyzedResponseORM).where(
                AnalyzedResponseORM.session_id == str(session_id)
            ).order_by(desc(AnalyzedResponseORM.created_at)).limit(limit)
            
            result = await self.db_session.execute(stmt)
            records = result.scalars().all()
            
            return [record.to_dict() for record in records]
        except Exception as e:
            print(f"Error retrieving analysis history: {e}")
            return []
    
    async def get_user_analytics(
        self,
        user_id: UUID,
        limit: int = 100,
    ) -> dict:
        """Get analytics for a user."""
        if not self.db_session:
            return {}
        
        try:
            from sqlalchemy import select, func
            
            # Get total analyzed responses
            stmt = select(func.count(AnalyzedResponseORM.id)).where(
                AnalyzedResponseORM.user_id == str(user_id)
            )
            result = await self.db_session.execute(stmt)
            total_responses = result.scalar() or 0
            
            # Get analysis method distribution
            stmt = select(
                AnalyzedResponseORM.analysis_method,
                func.count(AnalyzedResponseORM.id)
            ).where(
                AnalyzedResponseORM.user_id == str(user_id)
            ).group_by(AnalyzedResponseORM.analysis_method)
            
            result = await self.db_session.execute(stmt)
            method_distribution = {row[0]: row[1] for row in result.fetchall()}
            
            # Get average sentence counts
            stmt = select(
                func.avg(AnalyzedResponseORM.meta_sentence_count),
                func.avg(AnalyzedResponseORM.content_sentence_count),
            ).where(
                AnalyzedResponseORM.user_id == str(user_id)
            )
            
            result = await self.db_session.execute(stmt)
            avg_meta, avg_content = result.fetchone() or (0, 0)
            
            return {
                "total_responses": total_responses,
                "analysis_method_distribution": method_distribution,
                "average_meta_sentences": float(avg_meta) if avg_meta else 0,
                "average_content_sentences": float(avg_content) if avg_content else 0,
            }
        except Exception as e:
            print(f"Error retrieving user analytics: {e}")
            return {}
