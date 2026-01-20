"""Model for storing analyzed AI responses."""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column
from uuid import uuid4

from src.models.database import Base


class AnalyzedResponseORM(Base):
    """ORM model for analyzed responses."""
    
    __tablename__ = "analyzed_responses"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column(String(36), index=True)
    user_id: Mapped[str] = mapped_column(String(36), index=True)
    topic: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # Original response from AI
    original_response: Mapped[str] = mapped_column(Text)
    
    # Analyzed components
    meta_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Analysis metadata
    analysis_method: Mapped[str] = mapped_column(String(50))  # 'rule-based' or 'nlp'
    meta_sentence_count: Mapped[int] = mapped_column(Integer, default=0)
    content_sentence_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    analyzed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "topic": self.topic,
            "original_response": self.original_response,
            "meta_text": self.meta_text,
            "content_text": self.content_text,
            "analysis_method": self.analysis_method,
            "meta_sentence_count": self.meta_sentence_count,
            "content_sentence_count": self.content_sentence_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "analyzed_at": self.analyzed_at.isoformat() if self.analyzed_at else None,
        }
