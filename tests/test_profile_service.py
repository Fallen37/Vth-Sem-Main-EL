"""Tests for ProfileService."""

import pytest
from datetime import datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from src.models.database import Base
from src.models.user import UserORM
from src.models.enums import (
    UserRole,
    Syllabus,
    InteractionSpeed,
    InputType,
    ComprehensionLevel,
)
from src.models.learning_profile import (
    LearningProfileORM,
    LearningProfileUpdate,
    OutputMode,
    ExplanationStyle,
    InterfacePreferences,
)
from src.services.profile_service import ProfileService, Interaction


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
async def profile_service(db_session: AsyncSession):
    """Create a ProfileService instance."""
    return ProfileService(db_session)


class TestProfileService:
    """Tests for ProfileService."""

    @pytest.mark.asyncio
    async def test_get_profile_not_found(self, profile_service: ProfileService):
        """Test getting a profile that doesn't exist."""
        result = await profile_service.get_profile(uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_get_or_create_profile_creates_new(
        self, profile_service: ProfileService, test_user: UserORM
    ):
        """Test creating a new profile when one doesn't exist."""
        from uuid import UUID
        
        user_id = UUID(test_user.id)
        profile = await profile_service.get_or_create_profile(user_id)

        assert profile is not None
        assert profile.user_id == user_id
        # Check default values
        assert profile.preferred_output_mode.text is True
        assert profile.preferred_output_mode.audio is False
        assert profile.preferred_output_mode.visual is False
        assert profile.interaction_speed == InteractionSpeed.MEDIUM
        assert profile.preferred_explanation_style.use_examples is True

    @pytest.mark.asyncio
    async def test_get_or_create_profile_returns_existing(
        self, profile_service: ProfileService, test_user: UserORM
    ):
        """Test that get_or_create returns existing profile."""
        from uuid import UUID
        
        user_id = UUID(test_user.id)
        
        # Create profile
        profile1 = await profile_service.get_or_create_profile(user_id)
        
        # Get again - should return same profile
        profile2 = await profile_service.get_or_create_profile(user_id)

        assert profile1.id == profile2.id

    @pytest.mark.asyncio
    async def test_update_profile_output_mode(
        self, profile_service: ProfileService, test_user: UserORM
    ):
        """Test updating output mode preferences."""
        from uuid import UUID
        
        user_id = UUID(test_user.id)
        
        # Create profile first
        await profile_service.get_or_create_profile(user_id)

        # Update output mode
        updates = LearningProfileUpdate(
            preferred_output_mode=OutputMode(text=True, audio=True, visual=True)
        )
        updated = await profile_service.update_profile(user_id, updates)

        assert updated is not None
        assert updated.preferred_output_mode.audio is True
        assert updated.preferred_output_mode.visual is True

    @pytest.mark.asyncio
    async def test_update_profile_explanation_style(
        self, profile_service: ProfileService, test_user: UserORM
    ):
        """Test updating explanation style preferences."""
        from uuid import UUID
        
        user_id = UUID(test_user.id)
        
        # Create profile first
        await profile_service.get_or_create_profile(user_id)

        # Update explanation style
        updates = LearningProfileUpdate(
            preferred_explanation_style=ExplanationStyle(
                use_examples=True,
                use_diagrams=False,
                use_analogies=True,
                simplify_language=True,
                step_by_step=True,
            )
        )
        updated = await profile_service.update_profile(user_id, updates)

        assert updated is not None
        assert updated.preferred_explanation_style.use_diagrams is False
        assert updated.preferred_explanation_style.simplify_language is True

    @pytest.mark.asyncio
    async def test_record_interaction_updates_comprehension(
        self, profile_service: ProfileService, test_user: UserORM
    ):
        """Test that recording interactions updates comprehension history."""
        from uuid import UUID
        
        user_id = UUID(test_user.id)

        # Record an interaction with comprehension feedback
        interaction = Interaction(
            input_type=InputType.TEXT,
            topic_id="physics_motion",
            topic_name="Motion and Forces",
            comprehension_feedback=ComprehensionLevel.UNDERSTOOD,
        )
        profile = await profile_service.record_interaction(user_id, interaction)

        assert len(profile.comprehension_history) == 1
        assert profile.comprehension_history[0].topic_id == "physics_motion"
        assert profile.comprehension_history[0].comprehension_level == 1.0

    @pytest.mark.asyncio
    async def test_record_interaction_updates_output_mode(
        self, profile_service: ProfileService, test_user: UserORM
    ):
        """Test that recording interactions updates output mode preferences."""
        from uuid import UUID
        
        user_id = UUID(test_user.id)

        # Record an interaction with audio output mode
        interaction = Interaction(
            input_type=InputType.VOICE,
            output_mode_used=OutputMode(text=True, audio=True, visual=False),
        )
        profile = await profile_service.record_interaction(user_id, interaction)

        assert profile.preferred_output_mode.audio is True

    @pytest.mark.asyncio
    async def test_get_preferred_output_mode(
        self, profile_service: ProfileService, test_user: UserORM
    ):
        """Test getting preferred output mode."""
        from uuid import UUID
        
        user_id = UUID(test_user.id)
        
        output_mode = await profile_service.get_preferred_output_mode(user_id)

        assert output_mode is not None
        assert output_mode.text is True

    @pytest.mark.asyncio
    async def test_get_preferred_explanation_style(
        self, profile_service: ProfileService, test_user: UserORM
    ):
        """Test getting preferred explanation style."""
        from uuid import UUID
        
        user_id = UUID(test_user.id)
        
        style = await profile_service.get_preferred_explanation_style(user_id)

        assert style is not None
        assert style.use_examples is True
        assert style.step_by_step is True

    @pytest.mark.asyncio
    async def test_initialize_session_preferences(
        self, profile_service: ProfileService, test_user: UserORM
    ):
        """Test initializing session with stored preferences."""
        from uuid import UUID
        
        user_id = UUID(test_user.id)

        # First update the profile with custom preferences
        await profile_service.get_or_create_profile(user_id)
        updates = LearningProfileUpdate(
            preferred_output_mode=OutputMode(text=True, audio=True, visual=False),
            interaction_speed=InteractionSpeed.SLOW,
        )
        await profile_service.update_profile(user_id, updates)

        # Get session preferences
        prefs = await profile_service.initialize_session_preferences(user_id)

        assert prefs["output_mode"].audio is True
        assert prefs["interaction_speed"] == InteractionSpeed.SLOW

    @pytest.mark.asyncio
    async def test_comprehension_history_weighted_average(
        self, profile_service: ProfileService, test_user: UserORM
    ):
        """Test that comprehension history uses weighted average for updates."""
        from uuid import UUID
        
        user_id = UUID(test_user.id)

        # First interaction - understood
        interaction1 = Interaction(
            input_type=InputType.TEXT,
            topic_id="chemistry_atoms",
            topic_name="Atomic Structure",
            comprehension_feedback=ComprehensionLevel.UNDERSTOOD,
        )
        await profile_service.record_interaction(user_id, interaction1)

        # Second interaction - not understood
        interaction2 = Interaction(
            input_type=InputType.TEXT,
            topic_id="chemistry_atoms",
            topic_name="Atomic Structure",
            comprehension_feedback=ComprehensionLevel.NOT_UNDERSTOOD,
        )
        profile = await profile_service.record_interaction(user_id, interaction2)

        # Comprehension should be between 0 and 1 (weighted average)
        topic = profile.comprehension_history[0]
        assert topic.topic_id == "chemistry_atoms"
        assert 0 < topic.comprehension_level < 1
        assert topic.interaction_count == 2
