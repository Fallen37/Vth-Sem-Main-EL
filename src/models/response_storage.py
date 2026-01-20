"""Models for response storage and user preferences."""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Integer, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column
from uuid import uuid4
from typing import Optional, List

from src.models.database import Base


class StoredResponseORM(Base):
    """ORM model for storing AI explanations with block-level support."""
    
    __tablename__ = "stored_responses"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), index=True)
    session_id: Mapped[str] = mapped_column(String(36), index=True)
    topic: Mapped[str] = mapped_column(String(255), index=True)
    
    # Iteration tracking
    iteration_level: Mapped[int] = mapped_column(Integer, default=1)
    
    # Content
    explanation: Mapped[str] = mapped_column(Text)  # Current explanation
    meta_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Block-level content (new)
    blocks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array of blocks
    
    # User feedback
    liked: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    feedback_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Version history
    previous_versions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary."""
        import json
        return {
            "id": self.id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "topic": self.topic,
            "iteration_level": self.iteration_level,
            "explanation": self.explanation,
            "meta_text": self.meta_text,
            "content_text": self.content_text,
            "blocks": json.loads(self.blocks) if self.blocks else [],
            "liked": self.liked,
            "feedback_text": self.feedback_text,
            "previous_versions": json.loads(self.previous_versions) if self.previous_versions else [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def get_block_by_id(self, block_id: str) -> Optional[dict]:
        """Get a block by its ID."""
        import json
        if not self.blocks:
            return None
        
        blocks = json.loads(self.blocks)
        for block in blocks:
            if block.get("block_id") == block_id:
                return block
        return None
    
    def update_block_content(self, block_id: str, new_content_text: str, new_meta_text: Optional[str] = None) -> bool:
        """Update a block's content and increment its iteration level."""
        import json
        if not self.blocks:
            return False
        
        blocks = json.loads(self.blocks)
        for block in blocks:
            if block.get("block_id") == block_id:
                # Store previous version
                if "block_versions" not in block:
                    block["block_versions"] = []
                
                previous_version = {
                    "version": block.get("iteration_level", 1),
                    "content_text": block.get("content_text"),
                    "meta_text": block.get("meta_text"),
                    "timestamp": datetime.utcnow().isoformat(),
                }
                
                block["block_versions"].append(previous_version)
                
                # Keep only last 5 versions
                if len(block["block_versions"]) > 5:
                    block["block_versions"] = block["block_versions"][-5:]
                
                # Update content
                block["content_text"] = new_content_text
                if new_meta_text:
                    block["meta_text"] = new_meta_text
                block["iteration_level"] = block.get("iteration_level", 1) + 1
                block["updated_at"] = datetime.utcnow().isoformat()
                
                self.blocks = json.dumps(blocks)
                return True
        
        return False
    
    def add_block(self, block_id: str, content_text: str, meta_text: Optional[str] = None, topic_ref: Optional[str] = None) -> None:
        """Add a new block to the response."""
        import json
        blocks = []
        if self.blocks:
            blocks = json.loads(self.blocks)
        
        new_block = {
            "block_id": block_id,
            "content_text": content_text,
            "meta_text": meta_text,
            "topic_ref": topic_ref,
            "iteration_level": 1,
            "block_versions": [],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        blocks.append(new_block)
        self.blocks = json.dumps(blocks)


class UserPreferencesORM(Base):
    """ORM model for user learning preferences."""
    
    __tablename__ = "user_preferences"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    
    # Topics tracking
    topics_mastered: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array
    topics_confused: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array
    topics_in_progress: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array
    
    # Preferences
    preferred_difficulty: Mapped[str] = mapped_column(String(50), default="beginner")  # beginner, intermediate, advanced
    response_style: Mapped[str] = mapped_column(String(50), default="structured")  # structured, conversational, minimal
    
    # Learning summary
    history_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    total_responses_liked: Mapped[int] = mapped_column(Integer, default=0)
    total_responses_disliked: Mapped[int] = mapped_column(Integer, default=0)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary."""
        import json
        return {
            "id": self.id,
            "user_id": self.user_id,
            "topics_mastered": json.loads(self.topics_mastered) if self.topics_mastered else [],
            "topics_confused": json.loads(self.topics_confused) if self.topics_confused else [],
            "topics_in_progress": json.loads(self.topics_in_progress) if self.topics_in_progress else [],
            "preferred_difficulty": self.preferred_difficulty,
            "response_style": self.response_style,
            "history_summary": self.history_summary,
            "total_responses_liked": self.total_responses_liked,
            "total_responses_disliked": self.total_responses_disliked,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
