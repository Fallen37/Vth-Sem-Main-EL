"""Progress Tracker Service - tracks learning progress with child-friendly presentation."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.progress import (
    Progress,
    ProgressORM,
    ProgressCreate,
    ProgressUpdate,
    Achievement,
    AchievementORM,
    AchievementCreate,
    ProgressSummary,
    Topic,
)
from src.models.user import UserORM


# Achievement type definitions
class AchievementType:
    """Standard achievement types."""
    
    FIRST_TOPIC = "first_topic"
    FIVE_TOPICS = "five_topics"
    TEN_TOPICS = "ten_topics"
    MASTERY = "mastery"
    STREAK_3 = "streak_3"
    STREAK_7 = "streak_7"
    PERFECT_UNDERSTANDING = "perfect_understanding"


# Achievement definitions with titles and descriptions
ACHIEVEMENT_DEFINITIONS = {
    AchievementType.FIRST_TOPIC: {
        "title": "First Steps! 🌟",
        "description": "You learned your first topic! Great start on your science journey!",
    },
    AchievementType.FIVE_TOPICS: {
        "title": "Explorer! 🔭",
        "description": "You've explored 5 different topics! Keep discovering!",
    },
    AchievementType.TEN_TOPICS: {
        "title": "Science Star! ⭐",
        "description": "Amazing! You've covered 10 topics! You're becoming a science expert!",
    },
    AchievementType.MASTERY: {
        "title": "Topic Master! 🏆",
        "description": "You've mastered a topic with excellent understanding!",
    },
    AchievementType.STREAK_3: {
        "title": "On a Roll! 🎯",
        "description": "3 days of learning in a row! You're building great habits!",
    },
    AchievementType.STREAK_7: {
        "title": "Week Warrior! 💪",
        "description": "A whole week of learning! You're unstoppable!",
    },
    AchievementType.PERFECT_UNDERSTANDING: {
        "title": "Perfect Score! 🌈",
        "description": "You understood everything perfectly! Brilliant work!",
    },
}


# Review threshold - topics below this comprehension level need review
REVIEW_THRESHOLD = 0.6

# Mastery threshold - topics above this are considered mastered
MASTERY_THRESHOLD = 0.85


class ProgressTracker:
    """Service for tracking learning progress with child-friendly presentation.
    
    Requirements: 11.1, 11.4
    - Track topics covered and comprehension levels
    - Identify topics that need review based on comprehension patterns
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_topic_coverage(
        self,
        user_id: UUID,
        topic: Topic,
        comprehension: float,
    ) -> Progress:
        """
        Record topic coverage with comprehension level.

        Args:
            user_id: The user's ID
            topic: The topic being covered
            comprehension: Comprehension level (0.0 to 1.0)

        Returns:
            Updated or created Progress record

        Requirements: 11.1 - Track topics covered and comprehension levels
        """
        # Validate comprehension is in range
        comprehension = max(0.0, min(1.0, comprehension))

        # Check if progress record exists for this topic
        result = await self.db.execute(
            select(ProgressORM).where(
                ProgressORM.user_id == str(user_id),
                ProgressORM.topic_id == topic.topic_id,
            )
        )
        progress_orm = result.scalar_one_or_none()

        if progress_orm:
            # Update existing record with weighted average
            old_level = progress_orm.comprehension_level
            old_count = progress_orm.times_reviewed
            # Weighted average favoring recent interactions
            new_level = (old_level * old_count + comprehension * 2) / (old_count + 2)
            
            progress_orm.comprehension_level = round(new_level, 3)
            progress_orm.times_reviewed = old_count + 1
            progress_orm.last_reviewed_at = datetime.utcnow()
            progress_orm.updated_at = datetime.utcnow()
        else:
            # Create new progress record
            progress_orm = ProgressORM(
                id=str(uuid4()),
                user_id=str(user_id),
                topic_id=topic.topic_id,
                topic_name=topic.topic_name,
                grade=topic.grade,
                comprehension_level=comprehension,
                times_reviewed=1,
                last_reviewed_at=datetime.utcnow(),
            )
            self.db.add(progress_orm)

        await self.db.commit()
        await self.db.refresh(progress_orm)

        # Check for achievements after recording progress
        await self._check_and_award_achievements(user_id, comprehension)

        return self._orm_to_pydantic(progress_orm)

    async def get_progress(self, user_id: UUID) -> ProgressSummary:
        """
        Get a child-friendly progress summary.

        Args:
            user_id: The user's ID

        Returns:
            ProgressSummary with friendly visualizations

        Requirements: 11.2 - Display progress using child-friendly visualizations
        """
        # Get all progress records for user
        result = await self.db.execute(
            select(ProgressORM).where(ProgressORM.user_id == str(user_id))
        )
        progress_records = result.scalars().all()

        # Get user's grade to estimate total topics
        user_result = await self.db.execute(
            select(UserORM).where(UserORM.id == str(user_id))
        )
        user = user_result.scalar_one_or_none()
        
        # Estimate total topics based on grade (roughly 20 topics per grade level)
        total_topics = 20 if not user or not user.grade else 20

        # Calculate topics covered
        topics_covered = len(progress_records)

        # Calculate current streak
        current_streak = await self._calculate_streak(user_id)

        # Get recent achievements (last 5)
        recent_achievements = await self._get_recent_achievements(user_id, limit=5)

        # Identify strength areas (high comprehension)
        strength_areas = [
            Topic(
                topic_id=p.topic_id,
                topic_name=p.topic_name,
                grade=p.grade,
            )
            for p in progress_records
            if p.comprehension_level >= MASTERY_THRESHOLD
        ][:5]  # Top 5 strengths

        # Identify growth areas (low comprehension)
        growth_areas = [
            Topic(
                topic_id=p.topic_id,
                topic_name=p.topic_name,
                grade=p.grade,
            )
            for p in progress_records
            if p.comprehension_level < REVIEW_THRESHOLD
        ][:5]  # Top 5 areas needing growth

        return ProgressSummary(
            topics_covered=topics_covered,
            total_topics=total_topics,
            current_streak=current_streak,
            recent_achievements=recent_achievements,
            strength_areas=strength_areas,
            growth_areas=growth_areas,
        )

    async def get_topics_needing_review(self, user_id: UUID) -> list[Topic]:
        """
        Identify topics that need review based on comprehension patterns.

        Args:
            user_id: The user's ID

        Returns:
            List of topics needing review

        Requirements: 11.4 - Identify topics that need review based on comprehension patterns
        """
        result = await self.db.execute(
            select(ProgressORM).where(
                ProgressORM.user_id == str(user_id),
                ProgressORM.comprehension_level < REVIEW_THRESHOLD,
            ).order_by(ProgressORM.comprehension_level.asc())
        )
        progress_records = result.scalars().all()

        return [
            Topic(
                topic_id=p.topic_id,
                topic_name=p.topic_name,
                grade=p.grade,
            )
            for p in progress_records
        ]

    async def get_achievements(self, user_id: UUID) -> list[Achievement]:
        """
        Get all achievements for a user.

        Args:
            user_id: The user's ID

        Returns:
            List of earned achievements

        Requirements: 11.3 - Celebrate achievements with positive feedback
        """
        result = await self.db.execute(
            select(AchievementORM)
            .where(AchievementORM.user_id == str(user_id))
            .order_by(AchievementORM.earned_at.desc())
        )
        achievements = result.scalars().all()

        return [self._achievement_orm_to_pydantic(a) for a in achievements]

    async def _get_recent_achievements(
        self, user_id: UUID, limit: int = 5
    ) -> list[Achievement]:
        """Get recent achievements for a user."""
        result = await self.db.execute(
            select(AchievementORM)
            .where(AchievementORM.user_id == str(user_id))
            .order_by(AchievementORM.earned_at.desc())
            .limit(limit)
        )
        achievements = result.scalars().all()

        return [self._achievement_orm_to_pydantic(a) for a in achievements]

    async def _calculate_streak(self, user_id: UUID) -> int:
        """Calculate the current learning streak in days."""
        result = await self.db.execute(
            select(ProgressORM.last_reviewed_at)
            .where(ProgressORM.user_id == str(user_id))
            .order_by(ProgressORM.last_reviewed_at.desc())
        )
        dates = result.scalars().all()

        if not dates:
            return 0

        # Get unique dates
        unique_dates = set()
        for dt in dates:
            if dt:
                unique_dates.add(dt.date())

        if not unique_dates:
            return 0

        # Sort dates in descending order
        sorted_dates = sorted(unique_dates, reverse=True)
        
        # Check if the most recent activity was today or yesterday
        today = datetime.utcnow().date()
        if sorted_dates[0] < today - timedelta(days=1):
            return 0  # Streak broken

        # Count consecutive days
        streak = 1
        for i in range(1, len(sorted_dates)):
            expected_date = sorted_dates[i - 1] - timedelta(days=1)
            if sorted_dates[i] == expected_date:
                streak += 1
            else:
                break

        return streak

    async def _check_and_award_achievements(
        self, user_id: UUID, latest_comprehension: float
    ) -> list[Achievement]:
        """Check for and award any new achievements."""
        new_achievements = []

        # Get current stats
        result = await self.db.execute(
            select(func.count(ProgressORM.id)).where(
                ProgressORM.user_id == str(user_id)
            )
        )
        topics_count = result.scalar() or 0

        # Get existing achievements
        existing_result = await self.db.execute(
            select(AchievementORM.achievement_type).where(
                AchievementORM.user_id == str(user_id)
            )
        )
        existing_types = set(existing_result.scalars().all())

        # Check topic count achievements
        if topics_count >= 1 and AchievementType.FIRST_TOPIC not in existing_types:
            achievement = await self._award_achievement(
                user_id, AchievementType.FIRST_TOPIC
            )
            if achievement:
                new_achievements.append(achievement)

        if topics_count >= 5 and AchievementType.FIVE_TOPICS not in existing_types:
            achievement = await self._award_achievement(
                user_id, AchievementType.FIVE_TOPICS
            )
            if achievement:
                new_achievements.append(achievement)

        if topics_count >= 10 and AchievementType.TEN_TOPICS not in existing_types:
            achievement = await self._award_achievement(
                user_id, AchievementType.TEN_TOPICS
            )
            if achievement:
                new_achievements.append(achievement)

        # Check perfect understanding achievement
        if latest_comprehension >= 1.0:
            # Award perfect understanding (can be earned multiple times, but we track it)
            if AchievementType.PERFECT_UNDERSTANDING not in existing_types:
                achievement = await self._award_achievement(
                    user_id, AchievementType.PERFECT_UNDERSTANDING
                )
                if achievement:
                    new_achievements.append(achievement)

        # Check mastery achievement
        mastery_result = await self.db.execute(
            select(func.count(ProgressORM.id)).where(
                ProgressORM.user_id == str(user_id),
                ProgressORM.comprehension_level >= MASTERY_THRESHOLD,
            )
        )
        mastery_count = mastery_result.scalar() or 0
        
        if mastery_count >= 1 and AchievementType.MASTERY not in existing_types:
            achievement = await self._award_achievement(
                user_id, AchievementType.MASTERY
            )
            if achievement:
                new_achievements.append(achievement)

        # Check streak achievements
        streak = await self._calculate_streak(user_id)
        
        if streak >= 3 and AchievementType.STREAK_3 not in existing_types:
            achievement = await self._award_achievement(
                user_id, AchievementType.STREAK_3
            )
            if achievement:
                new_achievements.append(achievement)

        if streak >= 7 and AchievementType.STREAK_7 not in existing_types:
            achievement = await self._award_achievement(
                user_id, AchievementType.STREAK_7
            )
            if achievement:
                new_achievements.append(achievement)

        return new_achievements

    async def _award_achievement(
        self, user_id: UUID, achievement_type: str
    ) -> Optional[Achievement]:
        """Award an achievement to a user."""
        definition = ACHIEVEMENT_DEFINITIONS.get(achievement_type)
        if not definition:
            return None

        achievement_orm = AchievementORM(
            id=str(uuid4()),
            user_id=str(user_id),
            achievement_type=achievement_type,
            title=definition["title"],
            description=definition["description"],
        )

        self.db.add(achievement_orm)
        await self.db.commit()
        await self.db.refresh(achievement_orm)

        return self._achievement_orm_to_pydantic(achievement_orm)

    def _orm_to_pydantic(self, progress_orm: ProgressORM) -> Progress:
        """Convert ORM model to Pydantic model."""
        return Progress(
            id=UUID(progress_orm.id),
            user_id=UUID(progress_orm.user_id),
            topic_id=progress_orm.topic_id,
            topic_name=progress_orm.topic_name,
            grade=progress_orm.grade,
            comprehension_level=progress_orm.comprehension_level,
            times_reviewed=progress_orm.times_reviewed,
            last_reviewed_at=progress_orm.last_reviewed_at,
            created_at=progress_orm.created_at,
            updated_at=progress_orm.updated_at,
        )

    def _achievement_orm_to_pydantic(
        self, achievement_orm: AchievementORM
    ) -> Achievement:
        """Convert Achievement ORM model to Pydantic model."""
        return Achievement(
            id=UUID(achievement_orm.id),
            user_id=UUID(achievement_orm.user_id),
            achievement_type=achievement_orm.achievement_type,
            title=achievement_orm.title,
            description=achievement_orm.description,
            earned_at=achievement_orm.earned_at,
        )
