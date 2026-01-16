"""Chat API endpoints for message processing."""

from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db_session, require_current_user
from src.models.user import UserORM
from src.models.session import SessionORM
from src.models.enums import InputType, ComprehensionLevel, MessageRole
from src.services.chat_orchestrator import (
    ChatOrchestrator,
    ChatResponse,
    UserInput,
    ComprehensionOption,
    OutputModeOption,
)


router = APIRouter(prefix="/chat", tags=["Chat"])


class SendMessageRequest(BaseModel):
    """Request model for sending a message."""
    
    session_id: Optional[UUID] = None
    content: str = Field(min_length=1)
    input_type: InputType = InputType.TEXT
    source: MessageRole = MessageRole.STUDENT


class ComprehensionFeedbackRequest(BaseModel):
    """Request model for comprehension feedback."""
    
    session_id: UUID
    feedback: ComprehensionLevel


class PartSelectionRequest(BaseModel):
    """Request model for selecting an explanation part."""
    
    session_id: UUID
    part_id: str


class OutputModeChangeRequest(BaseModel):
    """Request model for changing output mode."""
    
    session_id: UUID
    mode_id: str


class SessionResponse(BaseModel):
    """Response model for session info."""
    
    session_id: UUID
    user_id: UUID
    is_new: bool = False


@router.post("/message", response_model=ChatResponse)
async def send_message(
    request: SendMessageRequest,
    user: UserORM = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ChatResponse:
    """
    Send a message and get a response from the AI tutor.
    
    Creates a new session if session_id is not provided.
    """
    user_id = UUID(user.id)
    
    # Get or create session
    if request.session_id:
        session_id = request.session_id
        # Verify session belongs to user
        result = await db.execute(
            select(SessionORM).where(
                SessionORM.id == str(session_id),
                SessionORM.user_id == str(user_id),
            )
        )
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )
    else:
        # Create new session
        session_id = uuid4()
        session = SessionORM(
            id=str(session_id),
            user_id=str(user_id),
        )
        db.add(session)
        await db.commit()
    
    # Create chat orchestrator
    orchestrator = ChatOrchestrator(db=db)
    
    # Process message
    user_input = UserInput(
        type=request.input_type,
        content=request.content,
        source=request.source,
    )
    
    response = await orchestrator.process_message(
        input=user_input,
        session_id=session_id,
        user_id=user_id,
        grade=user.grade,
        syllabus=user.syllabus,
    )
    
    return response


@router.post("/comprehension", response_model=ChatResponse)
async def submit_comprehension_feedback(
    request: ComprehensionFeedbackRequest,
    user: UserORM = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ChatResponse:
    """
    Submit comprehension feedback for the last explanation.
    
    Returns breakdown parts if feedback indicates partial or no understanding.
    """
    user_id = UUID(user.id)
    
    # Verify session belongs to user
    result = await db.execute(
        select(SessionORM).where(
            SessionORM.id == str(request.session_id),
            SessionORM.user_id == str(user_id),
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    
    # Create chat orchestrator
    orchestrator = ChatOrchestrator(db=db)
    
    # Handle comprehension feedback
    response = await orchestrator.handle_comprehension_feedback(
        feedback=request.feedback,
        session_id=request.session_id,
        user_id=user_id,
    )
    
    return response


@router.post("/part-selection", response_model=ChatResponse)
async def select_explanation_part(
    request: PartSelectionRequest,
    user: UserORM = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ChatResponse:
    """
    Select a part of the explanation for detailed explanation.
    """
    user_id = UUID(user.id)
    
    # Verify session belongs to user
    result = await db.execute(
        select(SessionORM).where(
            SessionORM.id == str(request.session_id),
            SessionORM.user_id == str(user_id),
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    
    # Create chat orchestrator
    orchestrator = ChatOrchestrator(db=db)
    
    # Handle part selection
    response = await orchestrator.handle_part_selection(
        part_id=request.part_id,
        session_id=request.session_id,
        user_id=user_id,
        grade=user.grade,
        syllabus=user.syllabus,
    )
    
    return response


@router.post("/output-mode", response_model=ChatResponse)
async def change_output_mode(
    request: OutputModeChangeRequest,
    user: UserORM = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ChatResponse:
    """
    Change the output mode for the session.
    """
    user_id = UUID(user.id)
    
    # Verify session belongs to user
    result = await db.execute(
        select(SessionORM).where(
            SessionORM.id == str(request.session_id),
            SessionORM.user_id == str(user_id),
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    
    # Create chat orchestrator
    orchestrator = ChatOrchestrator(db=db)
    
    # Change output mode
    response = await orchestrator.change_output_mode(
        mode_id=request.mode_id,
        session_id=request.session_id,
        user_id=user_id,
    )
    
    return response


@router.get("/comprehension-options", response_model=list[ComprehensionOption])
async def get_comprehension_options(
    user: UserORM = Depends(require_current_user),
) -> list[ComprehensionOption]:
    """Get available comprehension feedback options."""
    orchestrator = ChatOrchestrator()
    return orchestrator.get_comprehension_options()


@router.get("/output-mode-options", response_model=list[OutputModeOption])
async def get_output_mode_options(
    user: UserORM = Depends(require_current_user),
) -> list[OutputModeOption]:
    """Get available output mode options."""
    orchestrator = ChatOrchestrator()
    return orchestrator.get_output_mode_options()


@router.post("/session", response_model=SessionResponse)
async def create_session(
    user: UserORM = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> SessionResponse:
    """Create a new chat session."""
    user_id = UUID(user.id)
    session_id = uuid4()
    
    session = SessionORM(
        id=str(session_id),
        user_id=str(user_id),
    )
    db.add(session)
    await db.commit()
    
    return SessionResponse(
        session_id=session_id,
        user_id=user_id,
        is_new=True,
    )
