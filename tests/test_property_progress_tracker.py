"""Property-based tests for ProgressTracker.

Feature: autism-science-tutor, Property 26: Progress Recording
Validates: Requirements 11.1

This test validates that for any completed topic interaction with comprehension feedback,
the Progress model SHALL be updated with the topic and comprehension level.
"""

import pytest
from datetime import datetime
from uuid import uuid4, UUID

from hypothesis import given, settings, strategies as st, assume, HealthCheck
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from src.models.database import Base
from src.models.user import UserORM
from src.models.enums import UserRole, Syllabus
from src.models.progress import Topic, ProgressORM
from src.services.progress_tracker import ProgressTracker, REVIEW_THRESHOLD


# Strategies for generating valid test data
grade_strategy = st.integers(min_value=5, max_value=10)

topic_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N")),
    min_size=3,
    max_size=30,
).filter(lambda x: x.strip() and x.isalnum())

topic_name_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "Zs")),
    min_size=3,
    max_size=50,
).filter(lambda x: x.strip())

# Comprehension level between 0.0 and 1.0
comprehension_strategy = st.floats(min_value=0.0, max_value=1.0, allow_nan=False)

# Strategy for generating a Topic
topic_strategy = st.builds(
    Topic,
    topic_id=topic_id_strategy,
    topic_name=topic_name_strategy,
    grade=grade_strategy,
)


async def create_test_user(db_session: AsyncSession) -> UserORM:
    """Create a test user for property tests."""
    user_id = str(uuid4())
    user = UserORM(
        id=user_id,
        email=f"test_{user_id[:8]}@example.com",
        name="Test Student",
        role=UserRole.STUDENT,
        grade=7,
        syllabus=Syllabus.CBSE,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


class TestProgressRecording:
    """
    Property 26: Progress Recording
    
    For any completed topic interaction with comprehension feedback, the Progress model 
    SHALL be updated with the topic and comprehension level.
    
    Validates: Requirements 11.1
    """

    @given(
        topic=topic_strategy,
        comprehension=comprehension_strategy,
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_progress_records_topic_and_comprehension(
        self,
        topic: Topic,
        comprehension: float,
    ):
        """
        Feature: autism-science-tutor, Property 26: Progress Recording
        Validates: Requirements 11.1
        
        For any topic and comprehension level, recording topic coverage SHALL 
        create a Progress record with the correct topic_id, topic_name, grade, 
        and comprehension_level.
        """
        assume(topic.topic_id.strip())
        assume(topic.topic_name.strip())
        
        # Create fresh database for each test
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        async_session = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        
        async with async_session() as session:
            # Create test user
            user = await create_test_user(session)
            user_id = UUID(user.id)
            
            progress_tracker = ProgressTracker(session)
            
            # Record topic coverage
            progress = await progress_tracker.record_topic_coverage(
                user_id, topic, comprehension
            )
            
            # Property: Progress record SHALL contain the topic_id
            assert progress.topic_id == topic.topic_id, (
                f"Progress topic_id should be {topic.topic_id}, got {progress.topic_id}"
            )
            
            # Property: Progress record SHALL contain the topic_name
            assert progress.topic_name == topic.topic_name, (
                f"Progress topic_name should be {topic.topic_name}, got {progress.topic_name}"
            )
            
            # Property: Progress record SHALL contain the grade
            assert progress.grade == topic.grade, (
                f"Progress grade should be {topic.grade}, got {progress.grade}"
            )
            
            # Property: Progress record SHALL contain the comprehension level (clamped to 0-1)
            expected_comprehension = max(0.0, min(1.0, comprehension))
            assert progress.comprehension_level == expected_comprehension, (
                f"Progress comprehension_level should be {expected_comprehension}, "
                f"got {progress.comprehension_level}"
            )
            
            # Property: Progress record SHALL have times_reviewed >= 1
            assert progress.times_reviewed >= 1, (
                f"Progress times_reviewed should be >= 1, got {progress.times_reviewed}"
            )
        
        await engine.dispose()

    @given(
        topic=topic_strategy,
        comprehension_values=st.lists(
            comprehension_strategy,
            min_size=2,
            max_size=5,
        ),
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_repeated_topic_updates_progress(
        self,
        topic: Topic,
        comprehension_values: list[float],
    ):
        """
        Feature: autism-science-tutor, Property 26: Progress Recording
        Validates: Requirements 11.1
        
        For any sequence of comprehension feedback on the same topic, the Progress 
        model SHALL be updated with each interaction, incrementing times_reviewed.
        """
        assume(topic.topic_id.strip())
        assume(topic.topic_name.strip())
        assume(len(comprehension_values) >= 2)
        
        # Create fresh database for each test
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        async_session = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        
        async with async_session() as session:
            # Create test user
            user = await create_test_user(session)
            user_id = UUID(user.id)
            
            progress_tracker = ProgressTracker(session)
            
            # Record multiple interactions on the same topic
            for comprehension in comprehension_values:
                progress = await progress_tracker.record_topic_coverage(
                    user_id, topic, comprehension
                )
            
            # Property: times_reviewed SHALL equal the number of interactions
            assert progress.times_reviewed == len(comprehension_values), (
                f"times_reviewed should be {len(comprehension_values)}, "
                f"got {progress.times_reviewed}"
            )
            
            # Property: comprehension_level SHALL be between 0 and 1
            assert 0.0 <= progress.comprehension_level <= 1.0, (
                f"comprehension_level should be between 0 and 1, "
                f"got {progress.comprehension_level}"
            )
            
            # Property: last_reviewed_at SHALL be set
            assert progress.last_reviewed_at is not None, (
                "last_reviewed_at should be set after recording"
            )
        
        await engine.dispose()

    @given(
        topics=st.lists(
            topic_strategy,
            min_size=2,
            max_size=5,
            unique_by=lambda t: t.topic_id,
        ),
        comprehension=comprehension_strategy,
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_multiple_topics_recorded_separately(
        self,
        topics: list[Topic],
        comprehension: float,
    ):
        """
        Feature: autism-science-tutor, Property 26: Progress Recording
        Validates: Requirements 11.1
        
        For any set of distinct topics, each topic SHALL have its own Progress 
        record with independent comprehension tracking.
        """
        # Filter valid topics
        valid_topics = [t for t in topics if t.topic_id.strip() and t.topic_name.strip()]
        assume(len(valid_topics) >= 2)
        
        # Create fresh database for each test
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        async_session = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        
        async with async_session() as session:
            # Create test user
            user = await create_test_user(session)
            user_id = UUID(user.id)
            
            progress_tracker = ProgressTracker(session)
            
            # Record coverage for each topic
            recorded_progress = []
            for topic in valid_topics:
                progress = await progress_tracker.record_topic_coverage(
                    user_id, topic, comprehension
                )
                recorded_progress.append(progress)
            
            # Property: Each topic SHALL have its own Progress record
            recorded_topic_ids = {p.topic_id for p in recorded_progress}
            expected_topic_ids = {t.topic_id for t in valid_topics}
            assert recorded_topic_ids == expected_topic_ids, (
                f"All topics should be recorded. Expected {expected_topic_ids}, "
                f"got {recorded_topic_ids}"
            )
            
            # Property: Progress summary SHALL reflect all topics covered
            summary = await progress_tracker.get_progress(user_id)
            assert summary.topics_covered == len(valid_topics), (
                f"topics_covered should be {len(valid_topics)}, "
                f"got {summary.topics_covered}"
            )
        
        await engine.dispose()

    @given(
        topic=topic_strategy,
        comprehension=st.floats(min_value=-1.0, max_value=2.0, allow_nan=False),
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_comprehension_clamped_to_valid_range(
        self,
        topic: Topic,
        comprehension: float,
    ):
        """
        Feature: autism-science-tutor, Property 26: Progress Recording
        Validates: Requirements 11.1
        
        For any comprehension value (including out-of-range values), the Progress 
        model SHALL clamp the value to the valid range [0.0, 1.0].
        """
        assume(topic.topic_id.strip())
        assume(topic.topic_name.strip())
        
        # Create fresh database for each test
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        async_session = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        
        async with async_session() as session:
            # Create test user
            user = await create_test_user(session)
            user_id = UUID(user.id)
            
            progress_tracker = ProgressTracker(session)
            
            # Record topic coverage with potentially out-of-range comprehension
            progress = await progress_tracker.record_topic_coverage(
                user_id, topic, comprehension
            )
            
            # Property: comprehension_level SHALL be clamped to [0.0, 1.0]
            assert 0.0 <= progress.comprehension_level <= 1.0, (
                f"comprehension_level should be clamped to [0.0, 1.0], "
                f"got {progress.comprehension_level} for input {comprehension}"
            )
        
        await engine.dispose()

    @given(
        topic=topic_strategy,
        comprehension=comprehension_strategy,
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_progress_retrievable_after_recording(
        self,
        topic: Topic,
        comprehension: float,
    ):
        """
        Feature: autism-science-tutor, Property 26: Progress Recording
        Validates: Requirements 11.1
        
        For any recorded topic interaction, the Progress SHALL be retrievable 
        via get_progress and reflected in the summary.
        """
        assume(topic.topic_id.strip())
        assume(topic.topic_name.strip())
        
        # Create fresh database for each test
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        async_session = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        
        async with async_session() as session:
            # Create test user
            user = await create_test_user(session)
            user_id = UUID(user.id)
            
            progress_tracker = ProgressTracker(session)
            
            # Record topic coverage
            await progress_tracker.record_topic_coverage(user_id, topic, comprehension)
            
            # Property: Progress SHALL be reflected in get_progress summary
            summary = await progress_tracker.get_progress(user_id)
            assert summary.topics_covered >= 1, (
                "topics_covered should be at least 1 after recording"
            )
            
            # Property: Topic SHALL appear in strength or growth areas based on comprehension
            clamped_comprehension = max(0.0, min(1.0, comprehension))
            all_topic_ids = (
                [t.topic_id for t in summary.strength_areas] +
                [t.topic_id for t in summary.growth_areas]
            )
            
            # If comprehension is high enough for strength or low enough for growth,
            # the topic should appear in the appropriate list
            from src.services.progress_tracker import MASTERY_THRESHOLD
            if clamped_comprehension >= MASTERY_THRESHOLD:
                assert topic.topic_id in [t.topic_id for t in summary.strength_areas], (
                    f"Topic with comprehension {clamped_comprehension} should be in strength_areas"
                )
            elif clamped_comprehension < REVIEW_THRESHOLD:
                assert topic.topic_id in [t.topic_id for t in summary.growth_areas], (
                    f"Topic with comprehension {clamped_comprehension} should be in growth_areas"
                )
        
        await engine.dispose()
