"""Service for managing stored responses and user preferences."""

import json
from typing import Optional, List, Dict
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from src.models.response_storage import StoredResponseORM, UserPreferencesORM


class ResponseManagementService:
    """Manages AI explanations, user feedback, and learning preferences."""
    
    def __init__(self, db_session: AsyncSession):
        """Initialize the service."""
        self.db_session = db_session
        self._cache = {}  # In-memory cache for frequently accessed topics
    
    async def store_response(
        self,
        user_id: UUID,
        session_id: UUID,
        topic: str,
        explanation: str,
        meta_text: Optional[str] = None,
        content_text: Optional[str] = None,
    ) -> Dict:
        """
        Store an AI explanation.
        
        Args:
            user_id: User ID
            session_id: Session ID
            topic: Topic being explained
            explanation: Full explanation text
            meta_text: Conversational meta-text
            content_text: Educational content
        
        Returns:
            Stored response data
        """
        response = StoredResponseORM(
            user_id=str(user_id),
            session_id=str(session_id),
            topic=topic,
            explanation=explanation,
            meta_text=meta_text,
            content_text=content_text,
            iteration_level=1,
        )
        
        self.db_session.add(response)
        await self.db_session.commit()
        await self.db_session.refresh(response)
        
        # Update cache
        cache_key = f"{user_id}:{topic}"
        self._cache[cache_key] = response.to_dict()
        
        return response.to_dict()
    
    async def update_feedback(
        self,
        response_id: str,
        liked: bool,
        feedback_text: Optional[str] = None,
    ) -> Dict:
        """
        Update user feedback on a response.
        
        Args:
            response_id: Response ID
            liked: Whether user liked the explanation
            feedback_text: Optional feedback text
        
        Returns:
            Updated response data
        """
        stmt = select(StoredResponseORM).where(StoredResponseORM.id == response_id)
        result = await self.db_session.execute(stmt)
        response = result.scalar_one_or_none()
        
        if not response:
            raise ValueError(f"Response {response_id} not found")
        
        # Update feedback
        response.liked = liked
        response.feedback_text = feedback_text
        response.updated_at = datetime.utcnow()
        
        # Update user preferences
        await self._update_user_preferences(
            user_id=UUID(response.user_id),
            topic=response.topic,
            liked=liked,
        )
        
        await self.db_session.commit()
        await self.db_session.refresh(response)
        
        # Clear cache
        cache_key = f"{response.user_id}:{response.topic}"
        if cache_key in self._cache:
            del self._cache[cache_key]
        
        return response.to_dict()
    
    async def regenerate_explanation(
        self,
        response_id: str,
        new_explanation: str,
        new_meta_text: Optional[str] = None,
        new_content_text: Optional[str] = None,
    ) -> Dict:
        """
        Replace explanation with a simplified version.
        
        Args:
            response_id: Response ID to update
            new_explanation: New simplified explanation
            new_meta_text: New meta-text
            new_content_text: New content-text
        
        Returns:
            Updated response data
        """
        stmt = select(StoredResponseORM).where(StoredResponseORM.id == response_id)
        result = await self.db_session.execute(stmt)
        response = result.scalar_one_or_none()
        
        if not response:
            raise ValueError(f"Response {response_id} not found")
        
        # Store previous version
        previous_version = {
            "iteration_level": response.iteration_level,
            "explanation": response.explanation,
            "meta_text": response.meta_text,
            "content_text": response.content_text,
            "created_at": response.created_at.isoformat(),
            "updated_at": response.updated_at.isoformat(),
        }
        
        # Parse existing versions
        previous_versions = []
        if response.previous_versions:
            try:
                previous_versions = json.loads(response.previous_versions)
            except json.JSONDecodeError:
                previous_versions = []
        
        previous_versions.append(previous_version)
        
        # Update response
        response.explanation = new_explanation
        response.meta_text = new_meta_text
        response.content_text = new_content_text
        response.iteration_level += 1
        response.liked = None  # Reset feedback for new explanation
        response.feedback_text = None
        response.previous_versions = json.dumps(previous_versions)
        response.updated_at = datetime.utcnow()
        
        await self.db_session.commit()
        await self.db_session.refresh(response)
        
        # Clear cache
        cache_key = f"{response.user_id}:{response.topic}"
        if cache_key in self._cache:
            del self._cache[cache_key]
        
        return response.to_dict()
    
    async def regenerate_block(
        self,
        response_id: str,
        block_id: str,
        new_content_text: str,
        new_meta_text: Optional[str] = None,
    ) -> Dict:
        """
        Regenerate a specific block within a response.
        
        Args:
            response_id: Response ID containing the block
            block_id: Block ID to update
            new_content_text: New content for the block
            new_meta_text: New meta-text for the block
        
        Returns:
            Updated block data with iteration level and timestamp
        """
        stmt = select(StoredResponseORM).where(StoredResponseORM.id == response_id)
        result = await self.db_session.execute(stmt)
        response = result.scalar_one_or_none()
        
        if not response:
            raise ValueError(f"Response {response_id} not found")
        
        # Update the block
        if not response.update_block_content(block_id, new_content_text, new_meta_text):
            raise ValueError(f"Block {block_id} not found in response {response_id}")
        
        response.updated_at = datetime.utcnow()
        await self.db_session.commit()
        await self.db_session.refresh(response)
        
        # Clear cache
        cache_key = f"{response.user_id}:{response.topic}"
        if cache_key in self._cache:
            del self._cache[cache_key]
        
        # Get the updated block
        block = response.get_block_by_id(block_id)
        if not block:
            raise ValueError(f"Block {block_id} not found after update")
        
        return {
            "block_id": block_id,
            "new_content_text": block.get("content_text"),
            "iteration_level": block.get("iteration_level"),
            "timestamp": block.get("updated_at"),
            "analysis_method": "rule-based",
        }
    
    async def get_notebook(
        self,
        user_id: UUID,
        limit: Optional[int] = None,
    ) -> List[Dict]:
        """
        Get learning notebook (all liked responses).
        
        Args:
            user_id: User ID
            limit: Maximum number of responses
        
        Returns:
            List of liked responses
        """
        stmt = select(StoredResponseORM).where(
            StoredResponseORM.user_id == str(user_id),
            StoredResponseORM.liked == True,
        ).order_by(desc(StoredResponseORM.created_at))
        
        if limit:
            stmt = stmt.limit(limit)
        
        result = await self.db_session.execute(stmt)
        responses = result.scalars().all()
        
        # Format for notebook (only content_text, no meta_text)
        notebook = []
        for response in responses:
            notebook.append({
                "id": response.id,
                "topic": response.topic,
                "explanation": response.content_text or response.explanation,
                "iteration_level": response.iteration_level,
                "created_at": response.created_at.isoformat(),
            })
        
        return notebook
    
    async def _update_user_preferences(
        self,
        user_id: UUID,
        topic: str,
        liked: bool,
    ) -> None:
        """Update user preferences based on feedback."""
        stmt = select(UserPreferencesORM).where(UserPreferencesORM.user_id == str(user_id))
        result = await self.db_session.execute(stmt)
        prefs = result.scalar_one_or_none()
        
        if not prefs:
            # Create new preferences
            prefs = UserPreferencesORM(user_id=str(user_id))
            self.db_session.add(prefs)
        
        # Parse existing topics
        mastered = json.loads(prefs.topics_mastered) if prefs.topics_mastered else []
        confused = json.loads(prefs.topics_confused) if prefs.topics_confused else []
        in_progress = json.loads(prefs.topics_in_progress) if prefs.topics_in_progress else []
        
        # Update based on feedback
        if liked:
            prefs.total_responses_liked += 1
            if topic not in mastered:
                mastered.append(topic)
            if topic in confused:
                confused.remove(topic)
            if topic in in_progress:
                in_progress.remove(topic)
        else:
            prefs.total_responses_disliked += 1
            if topic not in confused:
                confused.append(topic)
            if topic in mastered:
                mastered.remove(topic)
            if topic not in in_progress:
                in_progress.append(topic)
        
        # Save updated lists
        prefs.topics_mastered = json.dumps(mastered)
        prefs.topics_confused = json.dumps(confused)
        prefs.topics_in_progress = json.dumps(in_progress)
        prefs.updated_at = datetime.utcnow()
        
        await self.db_session.commit()
    
    async def get_user_preferences(self, user_id: UUID) -> Dict:
        """Get user preferences."""
        stmt = select(UserPreferencesORM).where(UserPreferencesORM.user_id == str(user_id))
        result = await self.db_session.execute(stmt)
        prefs = result.scalar_one_or_none()
        
        if not prefs:
            # Create default preferences
            prefs = UserPreferencesORM(user_id=str(user_id))
            self.db_session.add(prefs)
            await self.db_session.commit()
        
        return prefs.to_dict()
    
    async def update_user_preferences(
        self,
        user_id: UUID,
        preferred_difficulty: Optional[str] = None,
        response_style: Optional[str] = None,
    ) -> Dict:
        """Update user preferences."""
        stmt = select(UserPreferencesORM).where(UserPreferencesORM.user_id == str(user_id))
        result = await self.db_session.execute(stmt)
        prefs = result.scalar_one_or_none()
        
        if not prefs:
            prefs = UserPreferencesORM(user_id=str(user_id))
            self.db_session.add(prefs)
        
        if preferred_difficulty:
            prefs.preferred_difficulty = preferred_difficulty
        if response_style:
            prefs.response_style = response_style
        
        prefs.updated_at = datetime.utcnow()
        await self.db_session.commit()
        await self.db_session.refresh(prefs)
        
        return prefs.to_dict()
    
    async def get_session_responses(
        self,
        session_id: UUID,
    ) -> List[Dict]:
        """Get all responses for a session."""
        stmt = select(StoredResponseORM).where(
            StoredResponseORM.session_id == str(session_id)
        ).order_by(StoredResponseORM.created_at)
        
        result = await self.db_session.execute(stmt)
        responses = result.scalars().all()
        
        return [r.to_dict() for r in responses]
    
    def get_cached_response(self, user_id: UUID, topic: str) -> Optional[Dict]:
        """Get cached response for a topic."""
        cache_key = f"{user_id}:{topic}"
        return self._cache.get(cache_key)
    
    def clear_cache(self):
        """Clear the in-memory cache."""
        self._cache.clear()
    
    async def get_block_by_id(self, response_id: str, block_id: str) -> Optional[Dict]:
        """Get a specific block from a response."""
        stmt = select(StoredResponseORM).where(StoredResponseORM.id == response_id)
        result = await self.db_session.execute(stmt)
        response = result.scalar_one_or_none()
        
        if not response:
            return None
        
        return response.get_block_by_id(block_id)
    
    async def add_block_to_response(
        self,
        response_id: str,
        block_id: str,
        content_text: str,
        meta_text: Optional[str] = None,
        topic_ref: Optional[str] = None,
    ) -> Dict:
        """Add a new block to an existing response."""
        stmt = select(StoredResponseORM).where(StoredResponseORM.id == response_id)
        result = await self.db_session.execute(stmt)
        response = result.scalar_one_or_none()
        
        if not response:
            raise ValueError(f"Response {response_id} not found")
        
        response.add_block(block_id, content_text, meta_text, topic_ref)
        response.updated_at = datetime.utcnow()
        
        await self.db_session.commit()
        await self.db_session.refresh(response)
        
        # Clear cache
        cache_key = f"{response.user_id}:{response.topic}"
        if cache_key in self._cache:
            del self._cache[cache_key]
        
        block = response.get_block_by_id(block_id)
        return block if block else {}
