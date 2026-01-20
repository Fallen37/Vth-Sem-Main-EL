"""API endpoints for response management and storage."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db_session, require_current_user
from src.models.user import UserORM
from src.services.response_management_service import ResponseManagementService


router = APIRouter(prefix="/responses", tags=["Responses"])


class StoreResponseRequest(BaseModel):
    """Request model for storing a response."""
    
    session_id: UUID
    topic: str = Field(min_length=1)
    explanation: str = Field(min_length=1)
    meta_text: Optional[str] = None
    content_text: Optional[str] = None


class UpdateFeedbackRequest(BaseModel):
    """Request model for updating feedback."""
    
    response_id: str
    liked: bool
    feedback_text: Optional[str] = None


class RegenerateExplanationRequest(BaseModel):
    """Request model for regenerating explanation."""
    
    response_id: str
    new_explanation: str = Field(min_length=1)
    new_meta_text: Optional[str] = None
    new_content_text: Optional[str] = None


class RegenerateBlockRequest(BaseModel):
    """Request model for regenerating a specific block."""
    
    response_id: str
    block_id: str
    query: str = Field(min_length=1)
    previous_content: str = Field(min_length=1)
    topic_ref: Optional[str] = None


class BlockUpdateResponse(BaseModel):
    """Response model for block update."""
    
    block_id: str
    new_content_text: str
    iteration_level: int
    timestamp: str
    analysis_method: str = "rule-based"


class UpdatePreferencesRequest(BaseModel):
    """Request model for updating user preferences."""
    
    preferred_difficulty: Optional[str] = None  # beginner, intermediate, advanced
    response_style: Optional[str] = None  # structured, conversational, minimal


class ResponseData(BaseModel):
    """Response data model."""
    
    id: str
    user_id: str
    session_id: str
    topic: str
    iteration_level: int
    explanation: str
    meta_text: Optional[str] = None
    content_text: Optional[str] = None
    liked: Optional[bool] = None
    feedback_text: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@router.post("/store")
async def store_response(
    request: StoreResponseRequest,
    user: UserORM = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ResponseData:
    """Store an AI explanation."""
    service = ResponseManagementService(db)
    
    result = await service.store_response(
        user_id=UUID(user.id),
        session_id=request.session_id,
        topic=request.topic,
        explanation=request.explanation,
        meta_text=request.meta_text,
        content_text=request.content_text,
    )
    
    return ResponseData(**result)


@router.post("/feedback")
async def update_feedback(
    request: UpdateFeedbackRequest,
    user: UserORM = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ResponseData:
    """Update feedback on a response."""
    service = ResponseManagementService(db)
    
    try:
        result = await service.update_feedback(
            response_id=request.response_id,
            liked=request.liked,
            feedback_text=request.feedback_text,
        )
        return ResponseData(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/regenerate")
async def regenerate_explanation(
    request: RegenerateExplanationRequest,
    user: UserORM = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ResponseData:
    """Regenerate a simplified explanation."""
    service = ResponseManagementService(db)
    
    try:
        result = await service.regenerate_explanation(
            response_id=request.response_id,
            new_explanation=request.new_explanation,
            new_meta_text=request.new_meta_text,
            new_content_text=request.new_content_text,
        )
        return ResponseData(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/regenerate-block", response_model=BlockUpdateResponse)
async def regenerate_block(
    request: RegenerateBlockRequest,
    user: UserORM = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> BlockUpdateResponse:
    """Regenerate a specific block within a response."""
    from src.services.llm_service import LLMService
    from src.services.response_analyzer_service import ResponseAnalyzerService
    
    service = ResponseManagementService(db)
    
    try:
        # Get the block to verify it exists
        block = await service.get_block_by_id(request.response_id, request.block_id)
        if not block:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Block {request.block_id} not found",
            )
        
        # Generate new content using LLM
        llm_service = LLMService()
        ai_response = await llm_service.generate_response(
            query=request.query,
            context=request.previous_content,
            user_grade=user.grade if hasattr(user, 'grade') else 6,
        )
        
        # Analyze response to separate meta-text and content
        analyzer_service = ResponseAnalyzerService(db_session=db)
        analysis = await analyzer_service.analyze_and_store(
            response_text=ai_response,
            session_id=None,
            user_id=UUID(user.id),
            topic=request.topic_ref,
        )
        
        # Update the block with new content
        result = await service.regenerate_block(
            response_id=request.response_id,
            block_id=request.block_id,
            new_content_text=analysis.get('content_text', ai_response),
            new_meta_text=analysis.get('meta_text'),
        )
        
        return BlockUpdateResponse(**result)
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error regenerating block: {str(e)}",
        )


@router.get("/notebook")
async def get_notebook(
    user: UserORM = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
    limit: Optional[int] = None,
):
    """Get learning notebook (all liked responses)."""
    service = ResponseManagementService(db)
    
    notebook = await service.get_notebook(
        user_id=UUID(user.id),
        limit=limit,
    )
    
    return {
        "user_id": user.id,
        "notebook_entries": notebook,
        "total_entries": len(notebook),
    }


@router.get("/preferences")
async def get_preferences(
    user: UserORM = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get user preferences."""
    service = ResponseManagementService(db)
    
    prefs = await service.get_user_preferences(UUID(user.id))
    
    return prefs


@router.put("/preferences")
async def update_preferences(
    request: UpdatePreferencesRequest,
    user: UserORM = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Update user preferences."""
    service = ResponseManagementService(db)
    
    prefs = await service.update_user_preferences(
        user_id=UUID(user.id),
        preferred_difficulty=request.preferred_difficulty,
        response_style=request.response_style,
    )
    
    return prefs


@router.get("/session/{session_id}")
async def get_session_responses(
    session_id: UUID,
    user: UserORM = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get all responses for a session."""
    service = ResponseManagementService(db)
    
    responses = await service.get_session_responses(session_id)
    
    return {
        "session_id": session_id,
        "responses": responses,
        "total_responses": len(responses),
    }


class AddBlockRequest(BaseModel):
    """Request model for adding a block to a response."""
    
    response_id: str
    block_id: str
    content_text: str = Field(min_length=1)
    meta_text: Optional[str] = None
    topic_ref: Optional[str] = None


@router.post("/add-block")
async def add_block(
    request: AddBlockRequest,
    user: UserORM = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Add a new block to an existing response."""
    service = ResponseManagementService(db)
    
    try:
        result = await service.add_block_to_response(
            response_id=request.response_id,
            block_id=request.block_id,
            content_text=request.content_text,
            meta_text=request.meta_text,
            topic_ref=request.topic_ref,
        )
        return {
            "block_id": request.block_id,
            "block": result,
            "status": "created",
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get("/block/{response_id}/{block_id}")
async def get_block(
    response_id: str,
    block_id: str,
    user: UserORM = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get a specific block from a response."""
    service = ResponseManagementService(db)
    
    block = await service.get_block_by_id(response_id, block_id)
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block {block_id} not found",
        )
    
    return {
        "response_id": response_id,
        "block": block,
    }
