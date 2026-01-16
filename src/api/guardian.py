"""Guardian API endpoints for guardian assistance features."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db_session, require_current_user, require_guardian
from src.models.user import UserORM
from src.models.enums import InputType
from src.services.guardian_service import (
    GuardianService,
    IndependenceMetrics,
    GuardianAlert,
)


router = APIRouter(prefix="/guardian", tags=["Guardian"])


class LinkGuardianRequest(BaseModel):
    """Request model for linking guardian to student."""
    
    student_id: UUID
    guardian_id: UUID


class GuardianInputRequest(BaseModel):
    """Request model for guardian input."""
    
    session_id: UUID
    content: str = Field(min_length=1)
    input_type: InputType = InputType.TEXT


class MessageResponse(BaseModel):
    """Response model for message."""
    
    id: UUID
    session_id: UUID
    role: str
    content: str
    timestamp: str


class IndependenceMetricsResponse(BaseModel):
    """Response model for independence metrics."""
    
    total_interactions: int
    student_interactions: int
    guardian_interactions: int
    independence_ratio: float
    trend: str
    weekly_breakdown: list[dict]


class SessionResponse(BaseModel):
    """Response model for session."""
    
    id: UUID
    user_id: UUID
    started_at: str
    ended_at: Optional[str] = None
    topics_covered: list[str]
    guardian_input_count: int
    student_input_count: int


class AlertResponse(BaseModel):
    """Response model for guardian alert."""
    
    id: UUID
    student_id: UUID
    guardian_id: UUID
    alert_type: str
    message: str
    created_at: str
    acknowledged: bool


@router.post("/link", status_code=status.HTTP_201_CREATED)
async def link_guardian_to_student(
    request: LinkGuardianRequest,
    user: UserORM = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Link a guardian to a student.
    
    Only the guardian or an admin can perform this action.
    """
    service = GuardianService(db)
    
    try:
        await service.link_guardian(request.student_id, request.guardian_id)
        return {"message": "Guardian linked successfully"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/input", response_model=MessageResponse)
async def record_guardian_input(
    request: GuardianInputRequest,
    user: UserORM = Depends(require_guardian),
    db: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    """
    Record input from a guardian.
    
    The input is logged separately from student inputs.
    """
    service = GuardianService(db)
    
    try:
        message = await service.record_guardian_input(
            session_id=request.session_id,
            content=request.content,
            input_type=request.input_type,
        )
        
        return MessageResponse(
            id=message.id,
            session_id=message.session_id,
            role=message.role.value,
            content=message.content,
            timestamp=message.timestamp.isoformat(),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get("/independence/{student_id}", response_model=IndependenceMetricsResponse)
async def get_independence_metrics(
    student_id: UUID,
    user: UserORM = Depends(require_guardian),
    db: AsyncSession = Depends(get_db_session),
) -> IndependenceMetricsResponse:
    """
    Get independence metrics for a linked student.
    
    Shows the ratio of student to guardian interactions.
    """
    service = GuardianService(db)
    
    # Verify guardian has access to this student
    try:
        await service._verify_guardian_access(UUID(user.id), student_id)
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    
    metrics = await service.get_independence_metrics(student_id)
    
    return IndependenceMetricsResponse(
        total_interactions=metrics.total_interactions,
        student_interactions=metrics.student_interactions,
        guardian_interactions=metrics.guardian_interactions,
        independence_ratio=metrics.independence_ratio,
        trend=metrics.trend,
        weekly_breakdown=metrics.weekly_breakdown,
    )


@router.get("/sessions/{student_id}", response_model=list[SessionResponse])
async def get_student_sessions(
    student_id: UUID,
    user: UserORM = Depends(require_guardian),
    db: AsyncSession = Depends(get_db_session),
) -> list[SessionResponse]:
    """
    Get session history for a linked student.
    """
    service = GuardianService(db)
    
    try:
        sessions = await service.get_session_history(student_id, UUID(user.id))
        
        return [
            SessionResponse(
                id=s.id,
                user_id=s.user_id,
                started_at=s.started_at.isoformat(),
                ended_at=s.ended_at.isoformat() if s.ended_at else None,
                topics_covered=s.topics_covered,
                guardian_input_count=s.guardian_input_count,
                student_input_count=s.student_input_count,
            )
            for s in sessions
        ]
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get("/alerts", response_model=list[AlertResponse])
async def get_alerts(
    unacknowledged_only: bool = False,
    user: UserORM = Depends(require_guardian),
    db: AsyncSession = Depends(get_db_session),
) -> list[AlertResponse]:
    """Get alerts for the current guardian."""
    service = GuardianService(db)
    
    alerts = await service.get_alerts(UUID(user.id), unacknowledged_only)
    
    return [
        AlertResponse(
            id=a.id,
            student_id=a.student_id,
            guardian_id=a.guardian_id,
            alert_type=a.alert_type,
            message=a.message,
            created_at=a.created_at.isoformat(),
            acknowledged=a.acknowledged,
        )
        for a in alerts
    ]


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: UUID,
    user: UserORM = Depends(require_guardian),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Acknowledge an alert."""
    service = GuardianService(db)
    
    acknowledged = await service.acknowledge_alert(alert_id)
    
    if not acknowledged:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found",
        )
    
    return {"message": "Alert acknowledged"}
