"""Property-based tests for ProfileService.

Feature: autism-science-tutor, Property 6: Profile Updates from Interactions
Validates: Requirements 2.2

This test validates that for any sequence of student interactions within a session,
the Learning_Profile SHALL be updated to reflect observed patterns (output mode usage,
comprehension feedback, interaction timing).
"""

import pytest
from datetime import datetime
from uuid import uuid4

from hypothesis import given, settings, strategies as st, assume, HealthCheck
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
    OutputMode,
    ExplanationStyle,
    InterfacePreferences,
    LearningProfileUpdate,
)
from src.models.enums import FontSize
from src.services.profile_service import ProfileService, Interaction


# Strategies for generating valid test data
input_type_strategy = st.sampled_from(list(InputType))
comprehension_level_strategy = st.sampled_from(list(ComprehensionLevel))
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

# Strategy for output mode
output_mode_strategy = st.builds(
    OutputMode,
    text=st.booleans(),
    audio=st.booleans(),
    visual=st.booleans(),
)

# Strategy for response time (in milliseconds)
response_time_strategy = st.integers(min_value=500, max_value=15000)

# Strategy for generating a single interaction
interaction_strategy = st.builds(
    Interaction,
    input_type=input_type_strategy,
    topic_id=st.one_of(st.none(), topic_id_strategy),
    topic_name=st.one_of(st.none(), topic_name_strategy),
    comprehension_feedback=st.one_of(st.none(), comprehension_level_strategy),
    output_mode_used=st.one_of(st.none(), output_mode_strategy),
    response_time_ms=st.one_of(st.none(), response_time_strategy),
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


class TestProfileUpdatesFromInteractions:
    """
    Property 6: Profile Updates from Interactions
    
    For any sequence of student interactions within a session, the Learning_Profile 
    SHALL be updated to reflect observed patterns (output mode usage, comprehension 
    feedback, interaction timing).
    
    Validates: Requirements 2.2
    """

    @given(
        output_mode=output_mode_strategy,
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_output_mode_updates_from_interaction(
        self,
        output_mode: OutputMode,
    ):
        """
        Feature: autism-science-tutor, Property 6: Profile Updates from Interactions
        Validates: Requirements 2.2
        
        For any interaction with an output mode used, the profile's preferred 
        output mode SHALL be updated to reflect the used modes.
        """
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
            user_id = user.id
            
            profile_service = ProfileService(session)
            
            # Record interaction with output mode
            interaction = Interaction(
                input_type=InputType.TEXT,
                output_mode_used=output_mode,
            )
            
            from uuid import UUID
            profile = await profile_service.record_interaction(UUID(user_id), interaction)
            
            # Property: If any output mode was used, it should be reflected in preferences
            if output_mode.text:
                assert profile.preferred_output_mode.text is True
            if output_mode.audio:
                assert profile.preferred_output_mode.audio is True
            if output_mode.visual:
                assert profile.preferred_output_mode.visual is True
        
        await engine.dispose()

    @given(
        topic_id=topic_id_strategy,
        comprehension=comprehension_level_strategy,
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_comprehension_feedback_updates_profile(
        self,
        topic_id: str,
        comprehension: ComprehensionLevel,
    ):
        """
        Feature: autism-science-tutor, Property 6: Profile Updates from Interactions
        Validates: Requirements 2.2
        
        For any interaction with comprehension feedback on a topic, the profile's 
        comprehension history SHALL be updated to include that topic.
        """
        assume(topic_id.strip())
        
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
            user_id = user.id
            
            profile_service = ProfileService(session)
            
            # Record interaction with comprehension feedback
            interaction = Interaction(
                input_type=InputType.TEXT,
                topic_id=topic_id,
                topic_name=f"Topic: {topic_id}",
                comprehension_feedback=comprehension,
            )
            
            from uuid import UUID
            profile = await profile_service.record_interaction(UUID(user_id), interaction)
            
            # Property: Comprehension history should contain the topic
            topic_ids = [t.topic_id for t in profile.comprehension_history]
            assert topic_id in topic_ids, (
                f"Topic {topic_id} should be in comprehension history"
            )
            
            # Property: Comprehension level should match expected value
            topic_entry = next(t for t in profile.comprehension_history if t.topic_id == topic_id)
            expected_levels = {
                ComprehensionLevel.UNDERSTOOD: 1.0,
                ComprehensionLevel.PARTIAL: 0.5,
                ComprehensionLevel.NOT_UNDERSTOOD: 0.0,
            }
            assert topic_entry.comprehension_level == expected_levels[comprehension], (
                f"Comprehension level should be {expected_levels[comprehension]}"
            )
        
        await engine.dispose()

    @given(
        response_time=response_time_strategy,
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_interaction_timing_updates_speed_preference(
        self,
        response_time: int,
    ):
        """
        Feature: autism-science-tutor, Property 6: Profile Updates from Interactions
        Validates: Requirements 2.2
        
        For any interaction with response timing, the profile's interaction speed 
        preference SHALL be updated based on the observed timing pattern.
        """
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
            user_id = user.id
            
            profile_service = ProfileService(session)
            
            # Record interaction with response time
            interaction = Interaction(
                input_type=InputType.TEXT,
                response_time_ms=response_time,
            )
            
            from uuid import UUID
            profile = await profile_service.record_interaction(UUID(user_id), interaction)
            
            # Property: Interaction speed should be set based on response time
            # Fast: < 3000ms, Medium: 3000-8000ms, Slow: > 8000ms
            if response_time < 3000:
                assert profile.interaction_speed == InteractionSpeed.FAST, (
                    f"Response time {response_time}ms should result in FAST speed"
                )
            elif response_time > 8000:
                assert profile.interaction_speed == InteractionSpeed.SLOW, (
                    f"Response time {response_time}ms should result in SLOW speed"
                )
            else:
                assert profile.interaction_speed == InteractionSpeed.MEDIUM, (
                    f"Response time {response_time}ms should result in MEDIUM speed"
                )
        
        await engine.dispose()

    @given(
        interactions=st.lists(
            st.tuples(topic_id_strategy, comprehension_level_strategy),
            min_size=2,
            max_size=5,
        ),
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_multiple_interactions_accumulate_in_profile(
        self,
        interactions: list[tuple[str, ComprehensionLevel]],
    ):
        """
        Feature: autism-science-tutor, Property 6: Profile Updates from Interactions
        Validates: Requirements 2.2
        
        For any sequence of interactions, all topics with comprehension feedback 
        SHALL be accumulated in the profile's comprehension history.
        """
        # Filter to unique topic IDs
        unique_topics = {}
        for topic_id, comprehension in interactions:
            if topic_id.strip():
                unique_topics[topic_id] = comprehension
        
        assume(len(unique_topics) >= 1)
        
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
            user_id = user.id
            
            profile_service = ProfileService(session)
            
            from uuid import UUID
            
            # Record all interactions
            for topic_id, comprehension in unique_topics.items():
                interaction = Interaction(
                    input_type=InputType.TEXT,
                    topic_id=topic_id,
                    topic_name=f"Topic: {topic_id}",
                    comprehension_feedback=comprehension,
                )
                await profile_service.record_interaction(UUID(user_id), interaction)
            
            # Get final profile
            profile = await profile_service.get_profile(UUID(user_id))
            
            # Property: All unique topics should be in comprehension history
            recorded_topic_ids = {t.topic_id for t in profile.comprehension_history}
            for topic_id in unique_topics.keys():
                assert topic_id in recorded_topic_ids, (
                    f"Topic {topic_id} should be in comprehension history"
                )
        
        await engine.dispose()

    @given(
        topic_id=topic_id_strategy,
        comprehension_sequence=st.lists(
            comprehension_level_strategy,
            min_size=2,
            max_size=5,
        ),
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_repeated_topic_interactions_update_comprehension(
        self,
        topic_id: str,
        comprehension_sequence: list[ComprehensionLevel],
    ):
        """
        Feature: autism-science-tutor, Property 6: Profile Updates from Interactions
        Validates: Requirements 2.2
        
        For any sequence of interactions on the same topic, the comprehension level 
        SHALL be updated using a weighted average that favors recent interactions.
        """
        assume(topic_id.strip())
        assume(len(comprehension_sequence) >= 2)
        
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
            user_id = user.id
            
            profile_service = ProfileService(session)
            
            from uuid import UUID
            
            # Record all interactions on the same topic
            for comprehension in comprehension_sequence:
                interaction = Interaction(
                    input_type=InputType.TEXT,
                    topic_id=topic_id,
                    topic_name=f"Topic: {topic_id}",
                    comprehension_feedback=comprehension,
                )
                await profile_service.record_interaction(UUID(user_id), interaction)
            
            # Get final profile
            profile = await profile_service.get_profile(UUID(user_id))
            
            # Property: Topic should have interaction count equal to sequence length
            topic_entry = next(
                (t for t in profile.comprehension_history if t.topic_id == topic_id),
                None
            )
            assert topic_entry is not None, f"Topic {topic_id} should be in history"
            assert topic_entry.interaction_count == len(comprehension_sequence), (
                f"Interaction count should be {len(comprehension_sequence)}, "
                f"got {topic_entry.interaction_count}"
            )
            
            # Property: Comprehension level should be between 0 and 1
            assert 0.0 <= topic_entry.comprehension_level <= 1.0, (
                f"Comprehension level should be between 0 and 1, "
                f"got {topic_entry.comprehension_level}"
            )
        
        await engine.dispose()


# Strategy for explanation style
explanation_style_strategy = st.builds(
    ExplanationStyle,
    use_examples=st.booleans(),
    use_diagrams=st.booleans(),
    use_analogies=st.booleans(),
    simplify_language=st.booleans(),
    step_by_step=st.booleans(),
)

# Strategy for interaction speed
interaction_speed_strategy = st.sampled_from(list(InteractionSpeed))

# Strategy for font size
font_size_strategy = st.sampled_from(list(FontSize))

# Strategy for interface preferences
interface_preferences_strategy = st.builds(
    InterfacePreferences,
    dark_mode=st.booleans(),
    font_size=font_size_strategy,
    reduced_motion=st.booleans(),
    high_contrast=st.booleans(),
)


class TestSessionPreferenceApplication:
    """
    Property 7: Session Preference Application
    
    For any user with an existing Learning_Profile, starting a new session SHALL 
    initialize the session with the stored preferences from that profile.
    
    Validates: Requirements 2.3
    """

    @given(
        output_mode=output_mode_strategy,
        explanation_style=explanation_style_strategy,
        interaction_speed=interaction_speed_strategy,
        interface_prefs=interface_preferences_strategy,
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_session_initializes_with_stored_preferences(
        self,
        output_mode: OutputMode,
        explanation_style: ExplanationStyle,
        interaction_speed: InteractionSpeed,
        interface_prefs: InterfacePreferences,
    ):
        """
        Feature: autism-science-tutor, Property 7: Session Preference Application
        Validates: Requirements 2.3
        
        For any user with an existing Learning_Profile containing arbitrary preferences,
        initializing session preferences SHALL return all stored preferences from that profile.
        """
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
            user_id = user.id
            
            profile_service = ProfileService(session)
            
            from uuid import UUID
            
            # Create profile with specific preferences
            await profile_service.get_or_create_profile(UUID(user_id))
            
            # Update profile with generated preferences
            from src.models.learning_profile import LearningProfileUpdate
            await profile_service.update_profile(
                UUID(user_id),
                LearningProfileUpdate(
                    preferred_output_mode=output_mode,
                    preferred_explanation_style=explanation_style,
                    interaction_speed=interaction_speed,
                    interface_preferences=interface_prefs,
                )
            )
            
            # Initialize session preferences (simulating new session start)
            session_prefs = await profile_service.initialize_session_preferences(UUID(user_id))
            
            # Property: Session preferences SHALL match stored profile preferences
            assert session_prefs["output_mode"].text == output_mode.text, (
                f"Output mode text should be {output_mode.text}"
            )
            assert session_prefs["output_mode"].audio == output_mode.audio, (
                f"Output mode audio should be {output_mode.audio}"
            )
            assert session_prefs["output_mode"].visual == output_mode.visual, (
                f"Output mode visual should be {output_mode.visual}"
            )
            
            # Property: Explanation style SHALL match stored preferences
            assert session_prefs["explanation_style"].use_examples == explanation_style.use_examples
            assert session_prefs["explanation_style"].use_diagrams == explanation_style.use_diagrams
            assert session_prefs["explanation_style"].use_analogies == explanation_style.use_analogies
            assert session_prefs["explanation_style"].simplify_language == explanation_style.simplify_language
            assert session_prefs["explanation_style"].step_by_step == explanation_style.step_by_step
            
            # Property: Interaction speed SHALL match stored preference
            assert session_prefs["interaction_speed"] == interaction_speed, (
                f"Interaction speed should be {interaction_speed}, got {session_prefs['interaction_speed']}"
            )
            
            # Property: Interface preferences SHALL match stored preferences
            assert session_prefs["interface_preferences"].dark_mode == interface_prefs.dark_mode
            assert session_prefs["interface_preferences"].font_size == interface_prefs.font_size
            assert session_prefs["interface_preferences"].reduced_motion == interface_prefs.reduced_motion
            assert session_prefs["interface_preferences"].high_contrast == interface_prefs.high_contrast
        
        await engine.dispose()

    @given(
        output_mode=output_mode_strategy,
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_session_preferences_reflect_profile_updates(
        self,
        output_mode: OutputMode,
    ):
        """
        Feature: autism-science-tutor, Property 7: Session Preference Application
        Validates: Requirements 2.3
        
        For any profile update, subsequent session initialization SHALL reflect 
        the updated preferences.
        """
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
            user_id = user.id
            
            profile_service = ProfileService(session)
            
            from uuid import UUID
            
            # Create profile with defaults
            await profile_service.get_or_create_profile(UUID(user_id))
            
            # Get initial session preferences
            initial_prefs = await profile_service.initialize_session_preferences(UUID(user_id))
            
            # Update profile with new output mode
            from src.models.learning_profile import LearningProfileUpdate
            await profile_service.update_profile(
                UUID(user_id),
                LearningProfileUpdate(preferred_output_mode=output_mode)
            )
            
            # Get updated session preferences
            updated_prefs = await profile_service.initialize_session_preferences(UUID(user_id))
            
            # Property: Updated session preferences SHALL reflect the profile update
            assert updated_prefs["output_mode"].text == output_mode.text
            assert updated_prefs["output_mode"].audio == output_mode.audio
            assert updated_prefs["output_mode"].visual == output_mode.visual
        
        await engine.dispose()

    @given(
        interaction_speed=interaction_speed_strategy,
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_session_preferences_include_all_required_fields(
        self,
        interaction_speed: InteractionSpeed,
    ):
        """
        Feature: autism-science-tutor, Property 7: Session Preference Application
        Validates: Requirements 2.3
        
        For any user with a Learning_Profile, session initialization SHALL return
        all required preference fields: output_mode, explanation_style, 
        interaction_speed, and interface_preferences.
        """
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
            user_id = user.id
            
            profile_service = ProfileService(session)
            
            from uuid import UUID
            
            # Create profile and update interaction speed
            await profile_service.get_or_create_profile(UUID(user_id))
            from src.models.learning_profile import LearningProfileUpdate
            await profile_service.update_profile(
                UUID(user_id),
                LearningProfileUpdate(interaction_speed=interaction_speed)
            )
            
            # Initialize session preferences
            session_prefs = await profile_service.initialize_session_preferences(UUID(user_id))
            
            # Property: All required fields SHALL be present
            assert "output_mode" in session_prefs, "output_mode should be in session preferences"
            assert "explanation_style" in session_prefs, "explanation_style should be in session preferences"
            assert "interaction_speed" in session_prefs, "interaction_speed should be in session preferences"
            assert "interface_preferences" in session_prefs, "interface_preferences should be in session preferences"
            
            # Property: Fields SHALL have correct types
            assert isinstance(session_prefs["output_mode"], OutputMode)
            assert isinstance(session_prefs["explanation_style"], ExplanationStyle)
            assert isinstance(session_prefs["interaction_speed"], InteractionSpeed)
            assert isinstance(session_prefs["interface_preferences"], InterfacePreferences)
        
        await engine.dispose()
