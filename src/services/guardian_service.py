"""Guardian Service - manages guardian assistance and independence tracking.

Requirements: 10.1, 10.2, 10.3, 10.4, 10.5
- Provide separate input section for guardian contributions
- Log guardian inputs separately from student inputs
- Track ratio of guardian assistance to student independence
- Acknowledge guardian source in response context
- Allow guardian to view session history and student progress
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import UserORM, User
from src.models.session import SessionORM, MessageORM, Session, Message
from src.models.enums import UserRole, MessageRole, InputType


class IndependenceMetrics(BaseModel):
    """Metrics tracking student independence from guardian assistance."""
    
    total_interactions: int = 0
    student_interactions: int = 0
    guardian_interactions: int = 0
    independence_ratio: float = 1.0
    trend: str = "stable"  # "improving", "stable", "declining"
    weekly_breakdown: list[dict] = Field(default_factory=list)


class WeeklyMetric(BaseModel):
    """Weekly breakdown of independence metrics."""
    
    week_start: datetime
    student_count: int
    guardian_count: int
    ratio: float


class AlertType:
    """Types of alerts that can be sent to guardians."""
    
    EMERGENCY = "emergency"
    LOW_COMPREHENSION = "low_comprehension"
    SESSION_SUMMARY = "session_summary"
    ACHIEVEMENT = "achievement"


class GuardianAlert(BaseModel):
    """Alert sent to a guardian."""
    
    id: UUID = Field(default_factory=uuid4)
    student_id: UUID
    guardian_id: UUID
    alert_type: str
    message: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    acknowledged: bool = False


class GuardianService:
    """Service for managing guardian assistance and independence tracking.
    
    Requirements: 10.1, 10.2, 10.3, 10.4, 10.5
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        # In-memory alert storage (in production, this would be a database table)
        self._alerts: list[GuardianAlert] = []

    async def link_guardian(
        self, student_id: UUID, guardian_id: UUID
    ) -> bool:
        """
        Link a guardian to a student.

        Args:
            student_id: The student's user ID
            guardian_id: The guardian's user ID

        Returns:
            True if linking was successful

        Requirements: 10.1 - Provide separate input section for guardian contributions
        """
        # Verify student exists and is a student
        student_result = await self.db.execute(
            select(UserORM).where(UserORM.id == str(student_id))
        )
        student = student_result.scalar_one_or_none()
        
        if not student:
            raise ValueError(f"Student {student_id} not found")
        if student.role != UserRole.STUDENT:
            raise ValueError(f"User {student_id} is not a student")

        # Verify guardian exists and is a guardian
        guardian_result = await self.db.execute(
            select(UserORM).where(UserORM.id == str(guardian_id))
        )
        guardian = guardian_result.scalar_one_or_none()
        
        if not guardian:
            raise ValueError(f"Guardian {guardian_id} not found")
        if guardian.role != UserRole.GUARDIAN:
            raise ValueError(f"User {guardian_id} is not a guardian")

        # Link student to guardian
        student.linked_guardian_id = str(guardian_id)
        
        # Add student to guardian's linked students
        linked_students = guardian.linked_student_ids or []
        if str(student_id) not in linked_students:
            linked_students.append(str(student_id))
            guardian.linked_student_ids = linked_students

        await self.db.commit()
        return True

    async def record_guardian_input(
        self,
        session_id: UUID,
        content: str,
        input_type: InputType = InputType.TEXT,
    ) -> Message:
        """
        Record input from a guardian, logging it with the guardian source.

        Args:
            session_id: The session ID
            content: The input content
            input_type: The type of input (text, voice, etc.)

        Returns:
            The created Message

        Requirements: 10.2 - Log guardian inputs separately from student inputs
        """
        # Get the session
        session_result = await self.db.execute(
            select(SessionORM).where(SessionORM.id == str(session_id))
        )
        session = session_result.scalar_one_or_none()
        
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Create message with GUARDIAN role
        message_id = str(uuid4())
        message_orm = MessageORM(
            id=message_id,
            session_id=str(session_id),
            role=MessageRole.GUARDIAN,
            input_type=input_type,
            content=content,
            timestamp=datetime.utcnow(),
        )
        
        self.db.add(message_orm)
        
        # Increment guardian input count on session
        session.guardian_input_count = (session.guardian_input_count or 0) + 1
        
        await self.db.commit()
        await self.db.refresh(message_orm)

        return Message(
            id=UUID(message_orm.id),
            session_id=UUID(message_orm.session_id),
            role=message_orm.role,
            input_type=message_orm.input_type,
            content=message_orm.content,
            timestamp=message_orm.timestamp,
        )

    async def record_student_input(
        self,
        session_id: UUID,
        content: str,
        input_type: InputType = InputType.TEXT,
    ) -> Message:
        """
        Record input from a student, logging it with the student source.

        Args:
            session_id: The session ID
            content: The input content
            input_type: The type of input (text, voice, etc.)

        Returns:
            The created Message

        Requirements: 10.2 - Log guardian inputs separately from student inputs
        """
        # Get the session
        session_result = await self.db.execute(
            select(SessionORM).where(SessionORM.id == str(session_id))
        )
        session = session_result.scalar_one_or_none()
        
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Create message with STUDENT role
        message_id = str(uuid4())
        message_orm = MessageORM(
            id=message_id,
            session_id=str(session_id),
            role=MessageRole.STUDENT,
            input_type=input_type,
            content=content,
            timestamp=datetime.utcnow(),
        )
        
        self.db.add(message_orm)
        
        # Increment student input count on session
        session.student_input_count = (session.student_input_count or 0) + 1
        
        await self.db.commit()
        await self.db.refresh(message_orm)

        return Message(
            id=UUID(message_orm.id),
            session_id=UUID(message_orm.session_id),
            role=message_orm.role,
            input_type=message_orm.input_type,
            content=message_orm.content,
            timestamp=message_orm.timestamp,
        )

    async def get_independence_metrics(
        self, student_id: UUID
    ) -> IndependenceMetrics:
        """
        Calculate independence metrics for a student.

        The independence ratio is calculated as:
        student_interactions / (student_interactions + guardian_interactions)

        Args:
            student_id: The student's user ID

        Returns:
            IndependenceMetrics with ratio and trend

        Requirements: 10.3 - Track ratio of guardian assistance to student independence
        """
        # Get all sessions for the student
        result = await self.db.execute(
            select(SessionORM).where(SessionORM.user_id == str(student_id))
        )
        sessions = result.scalars().all()

        if not sessions:
            return IndependenceMetrics()

        # Calculate totals across all sessions
        total_student = sum(s.student_input_count or 0 for s in sessions)
        total_guardian = sum(s.guardian_input_count or 0 for s in sessions)
        total_interactions = total_student + total_guardian

        # Calculate independence ratio
        if total_interactions == 0:
            independence_ratio = 1.0
        else:
            independence_ratio = total_student / total_interactions

        # Calculate weekly breakdown for trend analysis
        weekly_breakdown = await self._calculate_weekly_breakdown(student_id)
        
        # Determine trend based on recent weeks
        trend = self._calculate_trend(weekly_breakdown)

        return IndependenceMetrics(
            total_interactions=total_interactions,
            student_interactions=total_student,
            guardian_interactions=total_guardian,
            independence_ratio=round(independence_ratio, 3),
            trend=trend,
            weekly_breakdown=weekly_breakdown,
        )

    async def _calculate_weekly_breakdown(
        self, student_id: UUID, weeks: int = 4
    ) -> list[dict]:
        """Calculate weekly breakdown of independence metrics."""
        breakdown = []
        now = datetime.utcnow()
        
        for week_offset in range(weeks):
            week_end = now - timedelta(weeks=week_offset)
            week_start = week_end - timedelta(days=7)
            
            # Get sessions in this week
            result = await self.db.execute(
                select(SessionORM).where(
                    and_(
                        SessionORM.user_id == str(student_id),
                        SessionORM.started_at >= week_start,
                        SessionORM.started_at < week_end,
                    )
                )
            )
            sessions = result.scalars().all()
            
            student_count = sum(s.student_input_count or 0 for s in sessions)
            guardian_count = sum(s.guardian_input_count or 0 for s in sessions)
            total = student_count + guardian_count
            
            ratio = student_count / total if total > 0 else 1.0
            
            breakdown.append({
                "week_start": week_start.isoformat(),
                "student_count": student_count,
                "guardian_count": guardian_count,
                "ratio": round(ratio, 3),
            })
        
        return breakdown

    def _calculate_trend(self, weekly_breakdown: list[dict]) -> str:
        """Calculate trend from weekly breakdown."""
        if len(weekly_breakdown) < 2:
            return "stable"
        
        # Compare most recent week to previous weeks
        recent_ratio = weekly_breakdown[0].get("ratio", 1.0)
        older_ratios = [w.get("ratio", 1.0) for w in weekly_breakdown[1:]]
        
        if not older_ratios:
            return "stable"
        
        avg_older = sum(older_ratios) / len(older_ratios)
        
        # Determine trend based on difference
        diff = recent_ratio - avg_older
        if diff > 0.1:
            return "improving"
        elif diff < -0.1:
            return "declining"
        else:
            return "stable"

    async def get_session_history(
        self, student_id: UUID, guardian_id: UUID
    ) -> list[Session]:
        """
        Get session history for a linked student.

        Args:
            student_id: The student's user ID
            guardian_id: The guardian's user ID (for access control)

        Returns:
            List of sessions for the student

        Requirements: 10.5 - Guardian can view session history and student progress
        """
        # Verify guardian has access to this student
        await self._verify_guardian_access(guardian_id, student_id)

        # Get all sessions for the student
        result = await self.db.execute(
            select(SessionORM)
            .where(SessionORM.user_id == str(student_id))
            .order_by(SessionORM.started_at.desc())
        )
        sessions = result.scalars().all()

        return [self._session_orm_to_pydantic(s) for s in sessions]

    async def send_alert(
        self,
        student_id: UUID,
        alert_type: str,
        message: str,
    ) -> Optional[GuardianAlert]:
        """
        Send an alert to the student's linked guardian.

        Args:
            student_id: The student's user ID
            alert_type: Type of alert (emergency, low_comprehension, etc.)
            message: Alert message

        Returns:
            GuardianAlert if guardian exists, None otherwise

        Requirements: 10.4 - Acknowledge guardian source in response context
        """
        # Get the student's linked guardian
        student_result = await self.db.execute(
            select(UserORM).where(UserORM.id == str(student_id))
        )
        student = student_result.scalar_one_or_none()
        
        if not student or not student.linked_guardian_id:
            return None

        guardian_id = UUID(student.linked_guardian_id)
        
        alert = GuardianAlert(
            student_id=student_id,
            guardian_id=guardian_id,
            alert_type=alert_type,
            message=message,
        )
        
        # Store alert (in production, this would be persisted to database)
        self._alerts.append(alert)
        
        return alert

    async def get_alerts(
        self, guardian_id: UUID, unacknowledged_only: bool = False
    ) -> list[GuardianAlert]:
        """
        Get alerts for a guardian.

        Args:
            guardian_id: The guardian's user ID
            unacknowledged_only: If True, only return unacknowledged alerts

        Returns:
            List of alerts for the guardian
        """
        alerts = [a for a in self._alerts if a.guardian_id == guardian_id]
        
        if unacknowledged_only:
            alerts = [a for a in alerts if not a.acknowledged]
        
        return sorted(alerts, key=lambda a: a.created_at, reverse=True)

    async def acknowledge_alert(self, alert_id: UUID) -> bool:
        """
        Acknowledge an alert.

        Args:
            alert_id: The alert ID

        Returns:
            True if alert was found and acknowledged
        """
        for alert in self._alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                return True
        return False

    async def _verify_guardian_access(
        self, guardian_id: UUID, student_id: UUID
    ) -> bool:
        """
        Verify that a guardian has access to a student's data.

        Args:
            guardian_id: The guardian's user ID
            student_id: The student's user ID

        Returns:
            True if access is allowed

        Raises:
            PermissionError if access is denied

        Requirements: 10.5 - Guardian can only view linked student data
        """
        guardian_result = await self.db.execute(
            select(UserORM).where(UserORM.id == str(guardian_id))
        )
        guardian = guardian_result.scalar_one_or_none()
        
        if not guardian:
            raise ValueError(f"Guardian {guardian_id} not found")
        
        if guardian.role != UserRole.GUARDIAN:
            raise PermissionError(f"User {guardian_id} is not a guardian")
        
        linked_students = guardian.linked_student_ids or []
        if str(student_id) not in linked_students:
            raise PermissionError(
                f"Guardian {guardian_id} does not have access to student {student_id}"
            )
        
        return True

    async def is_guardian_input(self, message: Message) -> bool:
        """
        Check if a message is from a guardian.

        Args:
            message: The message to check

        Returns:
            True if the message is from a guardian

        Requirements: 10.2 - Log guardian inputs separately from student inputs
        """
        return message.role == MessageRole.GUARDIAN

    async def get_message_source(self, message: Message) -> str:
        """
        Get the source of a message (STUDENT or GUARDIAN).

        Args:
            message: The message to check

        Returns:
            "STUDENT" or "GUARDIAN"

        Requirements: 10.2 - Log guardian inputs separately from student inputs
        """
        return message.role.value.upper()

    def _session_orm_to_pydantic(self, session_orm: SessionORM) -> Session:
        """Convert Session ORM to Pydantic model."""
        messages = []
        for msg in session_orm.messages:
            messages.append(Message(
                id=UUID(msg.id),
                session_id=UUID(msg.session_id),
                role=msg.role,
                input_type=msg.input_type,
                content=msg.content,
                audio_url=msg.audio_url,
                visual_aid_url=msg.visual_aid_url,
                comprehension_feedback=msg.comprehension_feedback,
                timestamp=msg.timestamp,
            ))
        
        return Session(
            id=UUID(session_orm.id),
            user_id=UUID(session_orm.user_id),
            started_at=session_orm.started_at,
            ended_at=session_orm.ended_at,
            topics_covered=session_orm.topics_covered or [],
            comprehension_scores=session_orm.comprehension_scores or {},
            guardian_input_count=session_orm.guardian_input_count or 0,
            student_input_count=session_orm.student_input_count or 0,
            messages=messages,
        )
