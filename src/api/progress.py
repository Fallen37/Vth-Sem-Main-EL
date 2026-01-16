"""Progress API endpoints for tracking learning progress."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db_session, require_current_user
from src.models.user import UserORM
from src.models.progress import ProgressSummary, Achievement, Topic
from src.services.progress_tracker import ProgressTracker


router = APIRouter(prefix="/progress", tags=["Progress"])


class RecordProgressRequest(BaseModel):
    """Request model for recording topic progress."""
    
    topic_id: str = Field(min_length=1)
    topic_name: str = Field(min_length=1)
    grade: int = Field(ge=5, le=10)
    comprehension: float = Field(ge=0.0, le=1.0)


class ProgressResponse(BaseModel):
    """Response model for progress record."""
    
    id: UUID
    user_id: UUID
    topic_id: str
    topic_name: str
    grade: int
    comprehension_level: float
    times_reviewed: int


class TopicResponse(BaseModel):
    """Response model for topic."""
    
    topic_id: str
    topic_name: str
    grade: int


class AchievementResponse(BaseModel):
    """Response model for achievement."""
    
    id: UUID
    achievement_type: str
    title: str
    description: str
    earned_at: str


class ProgressSummaryResponse(BaseModel):
    """Response model for progress summary."""
    
    topics_covered: int
    total_topics: int
    current_streak: int
    recent_achievements: list[AchievementResponse]
    strength_areas: list[TopicResponse]
    growth_areas: list[TopicResponse]


@router.post("/record", response_model=ProgressResponse)
async def record_progress(
    request: RecordProgressRequest,
    user: UserORM = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ProgressResponse:
    """Record topic coverage with comprehension level."""
    user_id = UUID(user.id)
    
    topic = Topic(
        topic_id=request.topic_id,
        topic_name=request.topic_name,
        grade=request.grade,
    )
    
    tracker = ProgressTracker(db)
    progress = await tracker.record_topic_coverage(
        user_id=user_id,
        topic=topic,
        comprehension=request.comprehension,
    )
    
    return ProgressResponse(
        id=progress.id,
        user_id=progress.user_id,
        topic_id=progress.topic_id,
        topic_name=progress.topic_name,
        grade=progress.grade,
        comprehension_level=progress.comprehension_level,
        times_reviewed=progress.times_reviewed,
    )


@router.get("/summary", response_model=ProgressSummaryResponse)
async def get_progress_summary(
    user: UserORM = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ProgressSummaryResponse:
    """Get a child-friendly progress summary."""
    user_id = UUID(user.id)
    
    tracker = ProgressTracker(db)
    summary = await tracker.get_progress(user_id)
    
    return ProgressSummaryResponse(
        topics_covered=summary.topics_covered,
        total_topics=summary.total_topics,
        current_streak=summary.current_streak,
        recent_achievements=[
            AchievementResponse(
                id=a.id,
                achievement_type=a.achievement_type,
                title=a.title,
                description=a.description,
                earned_at=a.earned_at.isoformat(),
            )
            for a in summary.recent_achievements
        ],
        strength_areas=[
            TopicResponse(
                topic_id=t.topic_id,
                topic_name=t.topic_name,
                grade=t.grade,
            )
            for t in summary.strength_areas
        ],
        growth_areas=[
            TopicResponse(
                topic_id=t.topic_id,
                topic_name=t.topic_name,
                grade=t.grade,
            )
            for t in summary.growth_areas
        ],
    )


@router.get("/review-topics", response_model=list[TopicResponse])
async def get_topics_needing_review(
    user: UserORM = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> list[TopicResponse]:
    """Get topics that need review based on comprehension patterns."""
    user_id = UUID(user.id)
    
    tracker = ProgressTracker(db)
    topics = await tracker.get_topics_needing_review(user_id)
    
    return [
        TopicResponse(
            topic_id=t.topic_id,
            topic_name=t.topic_name,
            grade=t.grade,
        )
        for t in topics
    ]


@router.get("/achievements", response_model=list[AchievementResponse])
async def get_achievements(
    user: UserORM = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> list[AchievementResponse]:
    """Get all achievements for the current user."""
    user_id = UUID(user.id)
    
    tracker = ProgressTracker(db)
    achievements = await tracker.get_achievements(user_id)
    
    return [
        AchievementResponse(
            id=a.id,
            achievement_type=a.achievement_type,
            title=a.title,
            description=a.description,
            earned_at=a.earned_at.isoformat(),
        )
        for a in achievements
    ]
