"""Tests for ProgressTracker service."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4, UUID

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from src.models.database import Base
from src.models.user import UserORM
from src.models.enums import UserRole, Syllabus
from src.models.progress import Topic, ProgressORM, AchievementORM
from src.services.progress_tracker import (
    ProgressTracker,
    AchievementType,
    REVIEW_THRESHOLD,
    MASTERY_THRESHOLD,
)


@pytest.fixture
async def async_engine():
    """Create an async engine for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(async_engine):
    """Create a database session for testing."""
    async_session = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session


@pytest.fixture
async def test_user(db_session: AsyncSession):
    """Create a test user."""
    user_id = str(uuid4())
    user = UserORM(
        id=user_id,
        email="test@example.com",
        name="Test Student",
        role=UserRole.STUDENT,
        grade=7,
        syllabus=Syllabus.CBSE,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def progress_tracker(db_session: AsyncSession):
    """Create a ProgressTracker instance."""
    return ProgressTracker(db_session)


class TestProgressTracker:
    """Tests for ProgressTracker service."""

    @pytest.mark.asyncio
    async def test_record_topic_coverage_creates_new(
        self, progress_tracker: ProgressTracker, test_user: UserORM
    ):
        """Test recording coverage for a new topic."""
        user_id = UUID(test_user.id)
        topic = Topic(topic_id="physics_motion", topic_name="Motion and Forces", grade=7)

        progress = await progress_tracker.record_topic_coverage(
            user_id, topic, comprehension=0.8
        )

        assert progress is not None
        assert progress.topic_id == "physics_motion"
        assert progress.topic_name == "Motion and Forces"
        assert progress.comprehension_level == 0.8
        assert progress.times_reviewed == 1

    @pytest.mark.asyncio
    async def test_record_topic_coverage_updates_existing(
        self, progress_tracker: ProgressTracker, test_user: UserORM
    ):
        """Test recording coverage updates existing topic with weighted average."""
        user_id = UUID(test_user.id)
        topic = Topic(topic_id="physics_motion", topic_name="Motion and Forces", grade=7)

        # First recording
        await progress_tracker.record_topic_coverage(user_id, topic, comprehension=1.0)

        # Second recording with lower comprehension
        progress = await progress_tracker.record_topic_coverage(
            user_id, topic, comprehension=0.0
        )

        # Should be weighted average, not simple average
        assert progress.times_reviewed == 2
        assert 0 < progress.comprehension_level < 1.0

    @pytest.mark.asyncio
    async def test_record_topic_coverage_clamps_comprehension(
        self, progress_tracker: ProgressTracker, test_user: UserORM
    ):
        """Test that comprehension is clamped to 0-1 range."""
        user_id = UUID(test_user.id)
        topic = Topic(topic_id="physics_motion", topic_name="Motion", grade=7)

        # Test value above 1
        progress = await progress_tracker.record_topic_coverage(
            user_id, topic, comprehension=1.5
        )
        assert progress.comprehension_level == 1.0

    @pytest.mark.asyncio
    async def test_get_progress_empty(
        self, progress_tracker: ProgressTracker, test_user: UserORM
    ):
        """Test getting progress for user with no records."""
        user_id = UUID(test_user.id)

        summary = await progress_tracker.get_progress(user_id)

        assert summary.topics_covered == 0
        assert summary.current_streak == 0
        assert len(summary.strength_areas) == 0
        assert len(summary.growth_areas) == 0

    @pytest.mark.asyncio
    async def test_get_progress_with_topics(
        self, progress_tracker: ProgressTracker, test_user: UserORM
    ):
        """Test getting progress with recorded topics."""
        user_id = UUID(test_user.id)

        # Record some topics
        topics = [
            (Topic(topic_id="t1", topic_name="Topic 1", grade=7), 0.9),  # Strength
            (Topic(topic_id="t2", topic_name="Topic 2", grade=7), 0.4),  # Growth area
            (Topic(topic_id="t3", topic_name="Topic 3", grade=7), 0.7),  # Middle
        ]
        for topic, comp in topics:
            await progress_tracker.record_topic_coverage(user_id, topic, comp)

        summary = await progress_tracker.get_progress(user_id)

        assert summary.topics_covered == 3
        assert len(summary.strength_areas) == 1  # Only t1 >= MASTERY_THRESHOLD
        assert len(summary.growth_areas) == 1  # Only t2 < REVIEW_THRESHOLD

    @pytest.mark.asyncio
    async def test_get_topics_needing_review(
        self, progress_tracker: ProgressTracker, test_user: UserORM
    ):
        """Test identifying topics that need review."""
        user_id = UUID(test_user.id)

        # Record topics with varying comprehension
        topics = [
            (Topic(topic_id="t1", topic_name="Good Topic", grade=7), 0.9),
            (Topic(topic_id="t2", topic_name="Needs Review 1", grade=7), 0.3),
            (Topic(topic_id="t3", topic_name="Needs Review 2", grade=7), 0.5),
        ]
        for topic, comp in topics:
            await progress_tracker.record_topic_coverage(user_id, topic, comp)

        review_topics = await progress_tracker.get_topics_needing_review(user_id)

        assert len(review_topics) == 2
        # Should be ordered by comprehension ascending
        assert review_topics[0].topic_id == "t2"
        assert review_topics[1].topic_id == "t3"

    @pytest.mark.asyncio
    async def test_get_achievements_empty(
        self, progress_tracker: ProgressTracker, test_user: UserORM
    ):
        """Test getting achievements when none exist."""
        user_id = UUID(test_user.id)

        achievements = await progress_tracker.get_achievements(user_id)

        assert len(achievements) == 0

    @pytest.mark.asyncio
    async def test_first_topic_achievement(
        self, progress_tracker: ProgressTracker, test_user: UserORM
    ):
        """Test that first topic achievement is awarded."""
        user_id = UUID(test_user.id)
        topic = Topic(topic_id="t1", topic_name="First Topic", grade=7)

        await progress_tracker.record_topic_coverage(user_id, topic, comprehension=0.7)

        achievements = await progress_tracker.get_achievements(user_id)

        assert len(achievements) >= 1
        achievement_types = [a.achievement_type for a in achievements]
        assert AchievementType.FIRST_TOPIC in achievement_types

    @pytest.mark.asyncio
    async def test_mastery_achievement(
        self, progress_tracker: ProgressTracker, test_user: UserORM
    ):
        """Test that mastery achievement is awarded for high comprehension."""
        user_id = UUID(test_user.id)
        topic = Topic(topic_id="t1", topic_name="Mastered Topic", grade=7)

        # Record with high comprehension
        await progress_tracker.record_topic_coverage(user_id, topic, comprehension=0.9)

        achievements = await progress_tracker.get_achievements(user_id)

        achievement_types = [a.achievement_type for a in achievements]
        assert AchievementType.MASTERY in achievement_types

    @pytest.mark.asyncio
    async def test_perfect_understanding_achievement(
        self, progress_tracker: ProgressTracker, test_user: UserORM
    ):
        """Test that perfect understanding achievement is awarded."""
        user_id = UUID(test_user.id)
        topic = Topic(topic_id="t1", topic_name="Perfect Topic", grade=7)

        await progress_tracker.record_topic_coverage(user_id, topic, comprehension=1.0)

        achievements = await progress_tracker.get_achievements(user_id)

        achievement_types = [a.achievement_type for a in achievements]
        assert AchievementType.PERFECT_UNDERSTANDING in achievement_types

    @pytest.mark.asyncio
    async def test_five_topics_achievement(
        self, progress_tracker: ProgressTracker, test_user: UserORM
    ):
        """Test that five topics achievement is awarded."""
        user_id = UUID(test_user.id)

        # Record 5 topics
        for i in range(5):
            topic = Topic(topic_id=f"t{i}", topic_name=f"Topic {i}", grade=7)
            await progress_tracker.record_topic_coverage(user_id, topic, comprehension=0.7)

        achievements = await progress_tracker.get_achievements(user_id)

        achievement_types = [a.achievement_type for a in achievements]
        assert AchievementType.FIVE_TOPICS in achievement_types

    @pytest.mark.asyncio
    async def test_achievements_not_duplicated(
        self, progress_tracker: ProgressTracker, test_user: UserORM
    ):
        """Test that achievements are not awarded multiple times."""
        user_id = UUID(test_user.id)

        # Record multiple topics
        for i in range(3):
            topic = Topic(topic_id=f"t{i}", topic_name=f"Topic {i}", grade=7)
            await progress_tracker.record_topic_coverage(user_id, topic, comprehension=0.7)

        achievements = await progress_tracker.get_achievements(user_id)

        # Count first_topic achievements
        first_topic_count = sum(
            1 for a in achievements if a.achievement_type == AchievementType.FIRST_TOPIC
        )
        assert first_topic_count == 1
