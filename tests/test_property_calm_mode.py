"""Property-based tests for CalmModeService.

Feature: autism-science-tutor
Property 20: Break Mode Session Pause
Property 21: Emergency Alert Response

Validates: Requirements 9.2, 9.6
"""

import pytest
from datetime import datetime
from uuid import uuid4, UUID

from hypothesis import given, settings, strategies as st, assume, HealthCheck
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from src.models.database import Base
from src.models.user import UserORM
from src.models.session import SessionORM
from src.models.enums import UserRole, Syllabus
from src.services.calm_mode import (
    CalmModeService,
    BreakSession,
    BreathingSession,
    BreathingPattern,
    BreathingPhase,
    AudioStream,
    CalmingContent,
)
from src.services.guardian_service import GuardianService


async def create_test_student(db_session: AsyncSession) -> UserORM:
    """Create a test student for property tests."""
    user_id = str(uuid4())
    user = UserORM(
        id=user_id,
        email=f"student_{user_id[:8]}@example.com",
        name="Test Student",
        role=UserRole.STUDENT,
        grade=7,
        syllabus=Syllabus.CBSE,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def create_test_guardian(db_session: AsyncSession) -> UserORM:
    """Create a test guardian for property tests."""
    user_id = str(uuid4())
    user = UserORM(
        id=user_id,
        email=f"guardian_{user_id[:8]}@example.com",
        name="Test Guardian",
        role=UserRole.GUARDIAN,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def create_test_session(db_session: AsyncSession, user_id: str) -> SessionORM:
    """Create a test session for property tests."""
    session_id = str(uuid4())
    session = SessionORM(
        id=session_id,
        user_id=user_id,
        started_at=datetime.utcnow(),
        student_input_count=0,
        guardian_input_count=0,
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)
    return session


async def link_guardian_to_student(
    db_session: AsyncSession, student: UserORM, guardian: UserORM
) -> None:
    """Link a guardian to a student."""
    student.linked_guardian_id = guardian.id
    guardian.linked_student_ids = [student.id]
    await db_session.commit()


class TestBreakModeSessionPause:
    """
    Property 20: Break Mode Session Pause
    
    For any active session, activating break mode SHALL pause the session state 
    and prevent new learning interactions until break ends.
    
    Validates: Requirements 9.2
    """

    @given(
        num_activations=st.integers(min_value=1, max_value=5),
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_break_activation_pauses_session(
        self,
        num_activations: int,
    ):
        """
        Feature: autism-science-tutor, Property 20: Break Mode Session Pause
        Validates: Requirements 9.2
        
        For any user, activating break mode SHALL pause the session.
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
            # Create test student
            student = await create_test_student(session)
            user_id = UUID(student.id)
            
            # Create an active learning session
            await create_test_session(session, student.id)
            
            calm_service = CalmModeService(db=session)
            
            # Activate break mode
            break_session = await calm_service.activate_break(user_id)
            
            # Property: Break session SHALL be created
            assert break_session is not None, "Break session should be created"
            assert isinstance(break_session, BreakSession), "Should return BreakSession"
            
            # Property: Break session SHALL be active
            assert break_session.is_active, "Break session should be active"
            
            # Property: Session SHALL be paused
            is_paused = await calm_service.is_session_paused(user_id)
            assert is_paused is True, "Session should be paused during break"
            
            # Property: Multiple activations SHALL return same break session
            for _ in range(num_activations - 1):
                same_break = await calm_service.activate_break(user_id)
                assert same_break.session_id == break_session.session_id, (
                    "Multiple activations should return same break session"
                )
        
        await engine.dispose()

    @given(
        breathing_pattern=st.sampled_from(list(BreathingPattern)),
        cycles=st.integers(min_value=1, max_value=10),
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_break_with_breathing_exercise(
        self,
        breathing_pattern: BreathingPattern,
        cycles: int,
    ):
        """
        Feature: autism-science-tutor, Property 20: Break Mode Session Pause
        Validates: Requirements 9.2, 9.3
        
        For any break session with breathing exercise, the session SHALL remain 
        paused and breathing exercise SHALL be active.
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
            # Create test student
            student = await create_test_student(session)
            user_id = UUID(student.id)
            
            calm_service = CalmModeService(db=session)
            
            # Start breathing exercise (should auto-activate break)
            breathing_session = await calm_service.start_breathing_exercise(
                user_id, pattern=breathing_pattern, cycles=cycles
            )
            
            # Property: Breathing session SHALL be created
            assert breathing_session is not None, "Breathing session should be created"
            assert breathing_session.pattern == breathing_pattern, (
                f"Pattern should be {breathing_pattern}"
            )
            assert breathing_session.remaining_cycles == cycles, (
                f"Cycles should be {cycles}"
            )
            
            # Property: Session SHALL be paused
            is_paused = await calm_service.is_session_paused(user_id)
            assert is_paused is True, "Session should be paused during breathing exercise"
            
            # Property: Break session SHALL indicate breathing is active
            break_status = await calm_service.get_break_status(user_id)
            assert break_status is not None, "Break should be active"
            assert break_status.breathing_exercise_active is True, (
                "Breathing exercise should be marked active"
            )
        
        await engine.dispose()

    @given(
        play_music=st.booleans(),
        start_breathing=st.booleans(),
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_end_break_resumes_session(
        self,
        play_music: bool,
        start_breathing: bool,
    ):
        """
        Feature: autism-science-tutor, Property 20: Break Mode Session Pause
        Validates: Requirements 9.2
        
        For any break session, ending the break SHALL resume the session 
        and stop all break activities.
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
            # Create test student
            student = await create_test_student(session)
            user_id = UUID(student.id)
            
            calm_service = CalmModeService(db=session)
            
            # Activate break
            await calm_service.activate_break(user_id)
            
            # Optionally start activities
            if play_music:
                await calm_service.play_calm_music(user_id)
            if start_breathing:
                await calm_service.start_breathing_exercise(user_id)
            
            # Verify session is paused
            assert await calm_service.is_session_paused(user_id) is True
            
            # End break
            result = await calm_service.end_break(user_id)
            
            # Property: End break SHALL succeed
            assert result is True, "End break should succeed"
            
            # Property: Session SHALL no longer be paused
            is_paused = await calm_service.is_session_paused(user_id)
            assert is_paused is False, "Session should not be paused after break ends"
            
            # Property: Break status SHALL be None
            break_status = await calm_service.get_break_status(user_id)
            assert break_status is None, "Break status should be None after ending"
            
            # Property: Breathing status SHALL be None
            breathing_status = await calm_service.get_breathing_status(user_id)
            assert breathing_status is None, "Breathing should stop when break ends"
        
        await engine.dispose()

    @given(
        num_users=st.integers(min_value=2, max_value=5),
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_break_isolation_between_users(
        self,
        num_users: int,
    ):
        """
        Feature: autism-science-tutor, Property 20: Break Mode Session Pause
        Validates: Requirements 9.2
        
        For any set of users, one user's break SHALL NOT affect other users' sessions.
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
            # Create multiple students
            students = []
            for _ in range(num_users):
                student = await create_test_student(session)
                students.append(student)
            
            calm_service = CalmModeService(db=session)
            
            # Activate break for first user only
            first_user_id = UUID(students[0].id)
            await calm_service.activate_break(first_user_id)
            
            # Property: First user's session SHALL be paused
            assert await calm_service.is_session_paused(first_user_id) is True
            
            # Property: Other users' sessions SHALL NOT be paused
            for student in students[1:]:
                other_user_id = UUID(student.id)
                is_paused = await calm_service.is_session_paused(other_user_id)
                assert is_paused is False, (
                    f"User {student.id} should not be paused by another user's break"
                )
        
        await engine.dispose()


class TestEmergencyAlertResponse:
    """
    Property 21: Emergency Alert Response
    
    For any emergency button press, the System SHALL display calming content 
    AND send an alert to the linked guardian if one exists.
    
    Validates: Requirements 9.6
    """

    @given(
        has_guardian=st.booleans(),
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_emergency_displays_calming_content(
        self,
        has_guardian: bool,
    ):
        """
        Feature: autism-science-tutor, Property 21: Emergency Alert Response
        Validates: Requirements 9.6
        
        For any emergency trigger, calming content SHALL be displayed.
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
            # Create test student
            student = await create_test_student(session)
            user_id = UUID(student.id)
            
            guardian_service = GuardianService(session)
            
            # Optionally link guardian
            if has_guardian:
                guardian = await create_test_guardian(session)
                await link_guardian_to_student(session, student, guardian)
            
            calm_service = CalmModeService(db=session, guardian_service=guardian_service)
            
            # Trigger emergency
            calming_content, guardian_alerted = await calm_service.trigger_emergency_alert(user_id)
            
            # Property: Calming content SHALL be returned
            assert calming_content is not None, "Calming content should be returned"
            assert isinstance(calming_content, CalmingContent), (
                "Should return CalmingContent"
            )
            
            # Property: Calming content SHALL have a message
            assert calming_content.message, "Calming content should have a message"
            
            # Property: Session SHALL be paused (in break mode)
            is_paused = await calm_service.is_session_paused(user_id)
            assert is_paused is True, "Session should be paused during emergency"
            
            # Property: Break SHALL be marked as emergency
            break_status = await calm_service.get_break_status(user_id)
            assert break_status is not None, "Break should be active"
            assert break_status.is_emergency is True, "Break should be marked as emergency"
        
        await engine.dispose()

    @given(st.just(None))
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_emergency_alerts_linked_guardian(self, _):
        """
        Feature: autism-science-tutor, Property 21: Emergency Alert Response
        Validates: Requirements 9.6
        
        For any emergency with a linked guardian, an alert SHALL be sent.
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
            # Create test student and guardian
            student = await create_test_student(session)
            guardian = await create_test_guardian(session)
            user_id = UUID(student.id)
            guardian_id = UUID(guardian.id)
            
            # Link guardian to student
            await link_guardian_to_student(session, student, guardian)
            
            guardian_service = GuardianService(session)
            calm_service = CalmModeService(db=session, guardian_service=guardian_service)
            
            # Trigger emergency
            calming_content, guardian_alerted = await calm_service.trigger_emergency_alert(user_id)
            
            # Property: Guardian SHALL be alerted
            assert guardian_alerted is True, "Guardian should be alerted"
            
            # Property: Alert SHALL be in guardian's alerts
            alerts = await guardian_service.get_alerts(guardian_id)
            assert len(alerts) > 0, "Guardian should have received an alert"
            
            # Property: Alert SHALL be of type EMERGENCY
            emergency_alerts = [a for a in alerts if a.alert_type == "emergency"]
            assert len(emergency_alerts) > 0, "Should have emergency alert"
        
        await engine.dispose()

    @given(st.just(None))
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_emergency_without_guardian_still_shows_content(self, _):
        """
        Feature: autism-science-tutor, Property 21: Emergency Alert Response
        Validates: Requirements 9.6
        
        For any emergency without a linked guardian, calming content SHALL 
        still be displayed.
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
            # Create test student without guardian
            student = await create_test_student(session)
            user_id = UUID(student.id)
            
            guardian_service = GuardianService(session)
            calm_service = CalmModeService(db=session, guardian_service=guardian_service)
            
            # Trigger emergency
            calming_content, guardian_alerted = await calm_service.trigger_emergency_alert(user_id)
            
            # Property: Calming content SHALL still be returned
            assert calming_content is not None, "Calming content should be returned"
            assert calming_content.message, "Calming content should have a message"
            
            # Property: Guardian alert SHALL be False (no guardian linked)
            assert guardian_alerted is False, "Guardian should not be alerted (none linked)"
            
            # Property: Session SHALL still be paused
            is_paused = await calm_service.is_session_paused(user_id)
            assert is_paused is True, "Session should be paused during emergency"
        
        await engine.dispose()

    @given(
        num_emergencies=st.integers(min_value=1, max_value=3),
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_multiple_emergencies_send_multiple_alerts(
        self,
        num_emergencies: int,
    ):
        """
        Feature: autism-science-tutor, Property 21: Emergency Alert Response
        Validates: Requirements 9.6
        
        For any number of emergency triggers, each SHALL send an alert to guardian.
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
            # Create test student and guardian
            student = await create_test_student(session)
            guardian = await create_test_guardian(session)
            user_id = UUID(student.id)
            guardian_id = UUID(guardian.id)
            
            # Link guardian to student
            await link_guardian_to_student(session, student, guardian)
            
            guardian_service = GuardianService(session)
            calm_service = CalmModeService(db=session, guardian_service=guardian_service)
            
            # Trigger multiple emergencies (end break between each)
            for i in range(num_emergencies):
                await calm_service.trigger_emergency_alert(user_id)
                await calm_service.end_break(user_id)
            
            # Property: Guardian SHALL have received alerts for each emergency
            alerts = await guardian_service.get_alerts(guardian_id)
            emergency_alerts = [a for a in alerts if a.alert_type == "emergency"]
            assert len(emergency_alerts) == num_emergencies, (
                f"Should have {num_emergencies} emergency alerts, got {len(emergency_alerts)}"
            )
        
        await engine.dispose()

    @given(
        start_music=st.booleans(),
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_emergency_starts_calming_music(
        self,
        start_music: bool,
    ):
        """
        Feature: autism-science-tutor, Property 21: Emergency Alert Response
        Validates: Requirements 9.6
        
        For any emergency, calming music SHALL be started automatically.
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
            # Create test student
            student = await create_test_student(session)
            user_id = UUID(student.id)
            
            calm_service = CalmModeService(db=session)
            
            # Trigger emergency
            await calm_service.trigger_emergency_alert(user_id)
            
            # Property: Break SHALL have music playing
            break_status = await calm_service.get_break_status(user_id)
            assert break_status is not None, "Break should be active"
            assert break_status.music_playing is True, (
                "Music should be playing during emergency"
            )
        
        await engine.dispose()
