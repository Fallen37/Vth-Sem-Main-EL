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
    input_type: Optional[str] = "text"  # Accept string instead of enum
    source: Optional[str] = "student"  # Accept string instead of enum


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
    Saves messages to database for history tracking.
    """
    import time
    from src.models.session import MessageORM
    
    start_time = time.time()
    print(f"\n⏱️  [CHAT] Starting message processing at {start_time}")
    
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
    
    # Save user message to database
    user_message = MessageORM(
        session_id=str(session_id),
        role=MessageRole.STUDENT,
        input_type=InputType.TEXT,
        content=request.content,
    )
    db.add(user_message)
    await db.commit()
    print(f"⏱️  [CHAT] Saved user message: {time.time() - start_time:.2f}s")
    
    # Load previous messages for context
    result = await db.execute(
        select(MessageORM)
        .where(MessageORM.session_id == str(session_id))
        .order_by(MessageORM.timestamp)
    )
    previous_messages = result.scalars().all()
    print(f"⏱️  [CHAT] Loaded {len(previous_messages)} previous messages: {time.time() - start_time:.2f}s")
    
    # Build chat history for RAG service
    chat_history = [
        {
            "role": "user" if msg.role == MessageRole.STUDENT else "assistant",
            "content": msg.content
        }
        for msg in previous_messages
    ]
    
    # Use RAG service with chat history
    from src.services.rag_service import RAGService
    
    rag_start = time.time()
    rag_service = RAGService(db_session=db)
    rag_service.chat_history = chat_history
    
    # Chat with RAG
    result = await rag_service.chat(
        query=request.content,
        grade=user.grade,
    )
    rag_time = time.time() - rag_start
    print(f"⏱️  [CHAT] RAG service completed: {rag_time:.2f}s")
    
    # Save AI response to database
    ai_message = MessageORM(
        session_id=str(session_id),
        role=MessageRole.AI,
        input_type=InputType.TEXT,
        content=result['response'],
    )
    db.add(ai_message)
    await db.commit()
    print(f"⏱️  [CHAT] Saved AI response: {time.time() - start_time:.2f}s")
    
    # Analyze response to separate meta and educational content
    from src.services.response_analyzer_service import ResponseAnalyzerService
    from src.services.response_management_service import ResponseManagementService
    
    analyzer_start = time.time()
    analyzer_service = ResponseAnalyzerService(db_session=db)
    analysis = await analyzer_service.analyze_and_store(
        response_text=result['response'],
        session_id=session_id,
        user_id=user_id,
        topic=None,
    )
    analyzer_time = time.time() - analyzer_start
    print(f"⏱️  [CHAT] Response analysis completed: {analyzer_time:.2f}s")
    
    # Store response for later retrieval and feedback
    storage_start = time.time()
    storage_service = ResponseManagementService(db_session=db)

    # Use analyzed topic if available; fall back to a generic label
    storage_topic = analysis.get("topic") or "general"

    stored_response = await storage_service.store_response(
        user_id=user_id,
        session_id=session_id,
        topic=storage_topic,
        explanation=result['response'],
        meta_text=analysis.get('meta_text'),
        content_text=analysis.get('content_text'),
    )
    storage_time = time.time() - storage_start
    print(f"⏱️  [CHAT] Response storage completed: {storage_time:.2f}s")
    
    # Use only the educational content for the frontend
    content_for_frontend = analysis.get('content_text', result['response'])
    
    # Build response
    response = ChatResponse(
        message=content_for_frontend,
        sources=[],
        confidence=result.get('confidence', 0.7),
        suggested_responses=result.get('suggestions', []),
        is_explanation=True,
    )
    
    total_time = time.time() - start_time
    print(f"⏱️  [CHAT] Total time: {total_time:.2f}s (RAG: {rag_time:.2f}s, Analysis: {analyzer_time:.2f}s, Storage: {storage_time:.2f}s, DB: {total_time - rag_time - analyzer_time - storage_time:.2f}s)\n")
    
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


@router.get("/session/{session_id}/messages")
async def get_session_messages(
    session_id: UUID,
    user: UserORM = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get all messages for a session."""
    from src.models.session import MessageORM
    
    user_id = UUID(user.id)
    
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
    
    # Get all messages
    result = await db.execute(
        select(MessageORM)
        .where(MessageORM.session_id == str(session_id))
        .order_by(MessageORM.timestamp)
    )
    messages = result.scalars().all()
    
    return {
        "session_id": session_id,
        "messages": [
            {
                "id": msg.id,
                "role": "ai" if msg.role == MessageRole.AI else "user",
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
            }
            for msg in messages
        ]
    }


@router.get("/api-status")
async def get_api_status(
    user: UserORM = Depends(require_current_user),
):
    """Get the status of all API keys."""
    from src.services.api_key_manager import get_api_key_manager
    
    manager = get_api_key_manager()
    return manager.get_status()


@router.get("/analysis-history/{session_id}")
async def get_analysis_history(
    session_id: UUID,
    user: UserORM = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get analysis history for a session."""
    from src.services.response_analyzer_service import ResponseAnalyzerService
    
    user_id = UUID(user.id)
    
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
    
    analyzer_service = ResponseAnalyzerService(db_session=db)
    history = await analyzer_service.get_analysis_history(session_id)
    
    return {
        "session_id": session_id,
        "analysis_count": len(history),
        "analyses": history,
    }


@router.get("/analytics")
async def get_user_analytics(
    user: UserORM = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get analytics for the current user."""
    from src.services.response_analyzer_service import ResponseAnalyzerService
    
    user_id = UUID(user.id)
    
    analyzer_service = ResponseAnalyzerService(db_session=db)
    analytics = await analyzer_service.get_user_analytics(user_id)
    
    return {
        "user_id": user_id,
        "analytics": analytics,
    }
