"""Property-based tests for GuardianService.

Feature: autism-science-tutor, Property 22: Guardian Input Separation
Validates: Requirements 10.2

This test validates that for any message logged in a session, the source field 
SHALL correctly identify whether it came from STUDENT or GUARDIAN.
"""

import pytest
from datetime import datetime
from uuid import uuid4, UUID

from hypothesis import given, settings, strategies as st, assume, HealthCheck
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from src.models.database import Base
from src.models.user import UserORM
from src.models.session import SessionORM, MessageORM
from src.models.enums import UserRole, Syllabus, MessageRole, InputType
from src.services.guardian_service import GuardianService


# Strategies for generating valid test data
content_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "Zs", "P")),
    min_size=1,
    max_size=200,
).filter(lambda x: x.strip())

input_type_strategy = st.sampled_from([InputType.TEXT, InputType.VOICE, InputType.BUTTON])


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


class TestGuardianInputSeparation:
    """
    Property 22: Guardian Input Separation
    
    For any message logged in a session, the source field SHALL correctly identify 
    whether it came from STUDENT or GUARDIAN.
    
    Validates: Requirements 10.2
    """

    @given(
        content=content_strategy,
        input_type=input_type_strategy,
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_guardian_input_has_guardian_role(
        self,
        content: str,
        input_type: InputType,
    ):
        """
        Feature: autism-science-tutor, Property 22: Guardian Input Separation
        Validates: Requirements 10.2
        
        For any input recorded via record_guardian_input, the message role 
        SHALL be GUARDIAN.
        """
        assume(content.strip())
        
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
            # Create test student and session
            student = await create_test_student(session)
            test_session = await create_test_session(session, student.id)
            
            guardian_service = GuardianService(session)
            
            # Record guardian input
            message = await guardian_service.record_guardian_input(
                session_id=UUID(test_session.id),
                content=content,
                input_type=input_type,
            )
            
            # Property: Message role SHALL be GUARDIAN
            assert message.role == MessageRole.GUARDIAN, (
                f"Guardian input should have role GUARDIAN, got {message.role}"
            )
            
            # Property: Message source SHALL be identified as GUARDIAN
            source = await guardian_service.get_message_source(message)
            assert source == "GUARDIAN", (
                f"Guardian message source should be 'GUARDIAN', got {source}"
            )
            
            # Property: is_guardian_input SHALL return True
            is_guardian = await guardian_service.is_guardian_input(message)
            assert is_guardian is True, (
                "is_guardian_input should return True for guardian messages"
            )
        
        await engine.dispose()

    @given(
        content=content_strategy,
        input_type=input_type_strategy,
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_student_input_has_student_role(
        self,
        content: str,
        input_type: InputType,
    ):
        """
        Feature: autism-science-tutor, Property 22: Guardian Input Separation
        Validates: Requirements 10.2
        
        For any input recorded via record_student_input, the message role 
        SHALL be STUDENT.
        """
        assume(content.strip())
        
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
            # Create test student and session
            student = await create_test_student(session)
            test_session = await create_test_session(session, student.id)
            
            guardian_service = GuardianService(session)
            
            # Record student input
            message = await guardian_service.record_student_input(
                session_id=UUID(test_session.id),
                content=content,
                input_type=input_type,
            )
            
            # Property: Message role SHALL be STUDENT
            assert message.role == MessageRole.STUDENT, (
                f"Student input should have role STUDENT, got {message.role}"
            )
            
            # Property: Message source SHALL be identified as STUDENT
            source = await guardian_service.get_message_source(message)
            assert source == "STUDENT", (
                f"Student message source should be 'STUDENT', got {source}"
            )
            
            # Property: is_guardian_input SHALL return False
            is_guardian = await guardian_service.is_guardian_input(message)
            assert is_guardian is False, (
                "is_guardian_input should return False for student messages"
            )
        
        await engine.dispose()

    @given(
        student_contents=st.lists(content_strategy, min_size=1, max_size=5),
        guardian_contents=st.lists(content_strategy, min_size=1, max_size=5),
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_mixed_inputs_correctly_separated(
        self,
        student_contents: list[str],
        guardian_contents: list[str],
    ):
        """
        Feature: autism-science-tutor, Property 22: Guardian Input Separation
        Validates: Requirements 10.2
        
        For any sequence of mixed student and guardian inputs, each message 
        SHALL correctly identify its source.
        """
        # Filter valid contents
        valid_student = [c for c in student_contents if c.strip()]
        valid_guardian = [c for c in guardian_contents if c.strip()]
        assume(len(valid_student) >= 1)
        assume(len(valid_guardian) >= 1)
        
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
            # Create test student and session
            student = await create_test_student(session)
            test_session = await create_test_session(session, student.id)
            
            guardian_service = GuardianService(session)
            
            student_messages = []
            guardian_messages = []
            
            # Record student inputs
            for content in valid_student:
                msg = await guardian_service.record_student_input(
                    session_id=UUID(test_session.id),
                    content=content,
                )
                student_messages.append(msg)
            
            # Record guardian inputs
            for content in valid_guardian:
                msg = await guardian_service.record_guardian_input(
                    session_id=UUID(test_session.id),
                    content=content,
                )
                guardian_messages.append(msg)
            
            # Property: All student messages SHALL have STUDENT role
            for msg in student_messages:
                assert msg.role == MessageRole.STUDENT, (
                    f"Student message should have STUDENT role, got {msg.role}"
                )
            
            # Property: All guardian messages SHALL have GUARDIAN role
            for msg in guardian_messages:
                assert msg.role == MessageRole.GUARDIAN, (
                    f"Guardian message should have GUARDIAN role, got {msg.role}"
                )
            
            # Property: Student and guardian messages SHALL be distinguishable
            student_roles = {msg.role for msg in student_messages}
            guardian_roles = {msg.role for msg in guardian_messages}
            assert student_roles.isdisjoint(guardian_roles), (
                "Student and guardian messages should have distinct roles"
            )
        
        await engine.dispose()

    @given(
        student_count=st.integers(min_value=0, max_value=10),
        guardian_count=st.integers(min_value=0, max_value=10),
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_session_counts_match_inputs(
        self,
        student_count: int,
        guardian_count: int,
    ):
        """
        Feature: autism-science-tutor, Property 22: Guardian Input Separation
        Validates: Requirements 10.2
        
        For any number of student and guardian inputs, the session's input counts 
        SHALL accurately reflect the number of each type.
        """
        assume(student_count + guardian_count > 0)
        
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
            # Create test student and session
            student = await create_test_student(session)
            test_session = await create_test_session(session, student.id)
            session_id = UUID(test_session.id)
            
            guardian_service = GuardianService(session)
            
            # Record student inputs
            for i in range(student_count):
                await guardian_service.record_student_input(
                    session_id=session_id,
                    content=f"Student message {i}",
                )
            
            # Record guardian inputs
            for i in range(guardian_count):
                await guardian_service.record_guardian_input(
                    session_id=session_id,
                    content=f"Guardian message {i}",
                )
            
            # Refresh session to get updated counts
            await session.refresh(test_session)
            
            # Property: student_input_count SHALL equal number of student inputs
            assert test_session.student_input_count == student_count, (
                f"student_input_count should be {student_count}, "
                f"got {test_session.student_input_count}"
            )
            
            # Property: guardian_input_count SHALL equal number of guardian inputs
            assert test_session.guardian_input_count == guardian_count, (
                f"guardian_input_count should be {guardian_count}, "
                f"got {test_session.guardian_input_count}"
            )
        
        await engine.dispose()

    @given(
        content=content_strategy,
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_message_content_preserved(
        self,
        content: str,
    ):
        """
        Feature: autism-science-tutor, Property 22: Guardian Input Separation
        Validates: Requirements 10.2
        
        For any input content, the message SHALL preserve the original content 
        while correctly identifying the source.
        """
        assume(content.strip())
        
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
            # Create test student and session
            student = await create_test_student(session)
            test_session = await create_test_session(session, student.id)
            session_id = UUID(test_session.id)
            
            guardian_service = GuardianService(session)
            
            # Record same content from both sources
            student_msg = await guardian_service.record_student_input(
                session_id=session_id,
                content=content,
            )
            guardian_msg = await guardian_service.record_guardian_input(
                session_id=session_id,
                content=content,
            )
            
            # Property: Content SHALL be preserved for student message
            assert student_msg.content == content, (
                f"Student message content should be preserved"
            )
            
            # Property: Content SHALL be preserved for guardian message
            assert guardian_msg.content == content, (
                f"Guardian message content should be preserved"
            )
            
            # Property: Messages with same content SHALL still have different roles
            assert student_msg.role != guardian_msg.role, (
                "Messages with same content should have different roles based on source"
            )
        
        await engine.dispose()
