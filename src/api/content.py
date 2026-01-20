"""Content API endpoints for document upload and management."""

import os
import tempfile
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db_session, require_current_user, require_admin
from src.models.user import UserORM
from src.models.document import Document, ContentMetadata, ContentFilters
from src.models.enums import ContentType, Syllabus, DocumentStatus
from src.services.content_ingestion import ContentIngestionService, ProcessingResult


router = APIRouter(prefix="/content", tags=["Content"])


class DocumentResponse(BaseModel):
    """Response model for document."""
    
    id: UUID
    filename: str
    content_type: str
    grade: int
    syllabus: str
    subject: str
    chapter: str
    topic: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    chunk_count: Optional[int] = None
    status: str


class UploadResponse(BaseModel):
    """Response model for document upload."""
    
    document_id: UUID
    filename: str
    status: str


class ProcessResponse(BaseModel):
    """Response model for document processing."""
    
    document_id: UUID
    chunk_count: int
    embedding_status: str
    errors: list[str]


class CurriculumSummaryResponse(BaseModel):
    """Response model for curriculum summary."""
    
    total_documents: int
    by_grade: dict[str, int]
    by_syllabus: dict[str, int]
    by_subject: dict[str, int]
    by_chapter: dict[str, int]


class ChapterResponse(BaseModel):
    """Response model for a chapter."""
    
    chapter: str
    subject: str
    topic_count: int
    topics: list[str] = Field(default_factory=list)


class ChaptersResponse(BaseModel):
    """Response model for chapters by grade."""
    
    grade: int
    chapters: list[ChapterResponse]


class QueryRequest(BaseModel):
    """Request model for content query."""
    
    query: str = Field(min_length=1)
    grade: Optional[int] = Field(None, ge=5, le=10)
    syllabus: Optional[Syllabus] = None
    subject: Optional[str] = None
    chapter: Optional[str] = None
    topic: Optional[str] = None
    n_results: int = Field(5, ge=1, le=20)


class QueryResultItem(BaseModel):
    """Single query result item."""
    
    content: str
    similarity: float
    grade: Optional[int] = None
    syllabus: Optional[str] = None
    subject: Optional[str] = None
    chapter: Optional[str] = None
    topic: Optional[str] = None


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    grade: int = Form(..., ge=5, le=10),
    syllabus: Syllabus = Form(...),
    subject: str = Form(...),
    chapter: str = Form(...),
    content_type: ContentType = Form(...),
    topic: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),  # Comma-separated tags
    user: UserORM = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> UploadResponse:
    """
    Upload a document for processing.
    
    Supported formats: PDF, DOCX, TXT, PNG, JPG, JPEG, GIF, BMP, TIFF
    """
    # Validate file extension
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )
    
    ext = os.path.splitext(file.filename)[1].lower()
    supported_extensions = {".txt", ".pdf", ".docx", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff"}
    if ext not in supported_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format: {ext}. Supported: {supported_extensions}",
        )
    
    # Parse tags
    tag_list = []
    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    
    # Create metadata
    metadata = ContentMetadata(
        grade=grade,
        syllabus=syllabus,
        subject=subject,
        chapter=chapter,
        topic=topic,
        tags=tag_list,
        content_type=content_type,
    )
    
    # Save file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_path = tmp_file.name
    
    try:
        # Upload document
        service = ContentIngestionService(db)
        document_id = await service.upload_document(
            file_path=tmp_path,
            filename=file.filename,
            metadata=metadata,
        )
        
        return UploadResponse(
            document_id=document_id,
            filename=file.filename,
            status=DocumentStatus.PENDING.value,
        )
    finally:
        # Clean up temp file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.post("/process/{document_id}", response_model=ProcessResponse)
async def process_document(
    document_id: UUID,
    file: UploadFile = File(...),
    user: UserORM = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ProcessResponse:
    """
    Process an uploaded document: extract text, chunk, and embed.
    
    The file must be re-uploaded for processing.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )
    
    ext = os.path.splitext(file.filename)[1].lower()
    
    # Save file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_path = tmp_file.name
    
    try:
        service = ContentIngestionService(db)
        result = await service.process_document(document_id, tmp_path)
        
        return ProcessResponse(
            document_id=result.document_id,
            chunk_count=result.chunk_count,
            embedding_status=result.embedding_status,
            errors=result.errors,
        )
    finally:
        # Clean up temp file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.get("/documents", response_model=list[DocumentResponse])
async def list_documents(
    grade: Optional[int] = None,
    syllabus: Optional[Syllabus] = None,
    subject: Optional[str] = None,
    chapter: Optional[str] = None,
    topic: Optional[str] = None,
    content_type: Optional[ContentType] = None,
    user: UserORM = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> list[DocumentResponse]:
    """List documents with optional filters."""
    filters = ContentFilters(
        grade=grade,
        syllabus=syllabus,
        subject=subject,
        chapter=chapter,
        topic=topic,
        content_type=content_type,
    )
    
    service = ContentIngestionService(db)
    documents = await service.list_documents(filters)
    
    return [
        DocumentResponse(
            id=doc.id,
            filename=doc.filename,
            content_type=doc.content_type,
            grade=doc.grade,
            syllabus=doc.syllabus,
            subject=doc.subject,
            chapter=doc.chapter,
            topic=doc.topic,
            tags=doc.tags or [],
            chunk_count=doc.chunk_count,
            status=doc.status,
        )
        for doc in documents
    ]


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    user: UserORM = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> DocumentResponse:
    """Get a document by ID."""
    service = ContentIngestionService(db)
    doc = await service.get_document(document_id)
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    
    return DocumentResponse(
        id=doc.id,
        filename=doc.filename,
        content_type=doc.content_type,
        grade=doc.grade,
        syllabus=doc.syllabus,
        subject=doc.subject,
        chapter=doc.chapter,
        topic=doc.topic,
        tags=doc.tags or [],
        chunk_count=doc.chunk_count,
        status=doc.status,
    )


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    user: UserORM = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """Delete a document (admin only)."""
    service = ContentIngestionService(db)
    deleted = await service.delete_document(document_id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )


@router.post("/query", response_model=list[QueryResultItem])
async def query_content(
    request: QueryRequest,
    user: UserORM = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> list[QueryResultItem]:
    """Query content by curriculum filters."""
    filters = ContentFilters(
        grade=request.grade,
        syllabus=request.syllabus,
        subject=request.subject,
        chapter=request.chapter,
        topic=request.topic,
    )
    
    service = ContentIngestionService(db)
    results = await service.query_by_curriculum(
        query_text=request.query,
        filters=filters,
        n_results=request.n_results,
    )
    
    return [
        QueryResultItem(
            content=r["content"],
            similarity=r["similarity"],
            grade=r.get("grade"),
            syllabus=r.get("syllabus"),
            subject=r.get("subject"),
            chapter=r.get("chapter"),
            topic=r.get("topic"),
        )
        for r in results
    ]


@router.get("/summary", response_model=CurriculumSummaryResponse)
async def get_curriculum_summary(
    user: UserORM = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> CurriculumSummaryResponse:
    """Get a summary of available curriculum content."""
    service = ContentIngestionService(db)
    summary = await service.get_curriculum_summary()
    
    return CurriculumSummaryResponse(
        total_documents=summary["total_documents"],
        by_grade=summary["by_grade"],
        by_syllabus=summary["by_syllabus"],
        by_subject=summary["by_subject"],
        by_chapter=summary["by_chapter"],
    )


@router.get("/chapters/{grade}/{chapter}", response_model=dict)
async def get_chapter_content(
    grade: int,
    chapter: str,
    user: UserORM = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Get topics for a specific chapter."""
    from sqlalchemy import select, func
    from src.models.document import DocumentORM
    
    # Decode the chapter name
    import urllib.parse
    chapter_decoded = urllib.parse.unquote(chapter)
    
    print(f"DEBUG: Fetching topics for grade {grade}, chapter {chapter_decoded}")
    
    # Query documents for this chapter to get topics
    stmt = select(DocumentORM.topic).where(
        DocumentORM.grade == grade,
        DocumentORM.chapter == chapter_decoded,
        DocumentORM.topic.isnot(None)
    ).distinct()
    
    result = await db.execute(stmt)
    topics = [row[0] for row in result.fetchall() if row[0]]
    
    # If no topics found, return empty list
    if not topics:
        topics = []
    
    return {
        "grade": grade,
        "chapter": chapter_decoded,
        "topics": topics,
    }


@router.get("/chapters/{grade}", response_model=ChaptersResponse)
async def get_chapters_by_grade(
    grade: int,
    user: UserORM = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ChaptersResponse:
    """Get all chapters available for a specific grade."""
    from sqlalchemy import select, func
    from src.models.document import DocumentORM
    
    print(f"\n🔍 [API] GET /chapters/{grade}")
    print(f"   User: {user.id}, Grade: {grade}")
    
    # Query chapters for the grade with topics
    stmt = select(
        DocumentORM.chapter,
        DocumentORM.subject,
        func.count(DocumentORM.id).label("topic_count"),
        func.group_concat(DocumentORM.topic).label("topics")
    ).where(
        DocumentORM.grade == grade,
        DocumentORM.chapter.isnot(None)
    ).group_by(
        DocumentORM.chapter,
        DocumentORM.subject
    ).order_by(DocumentORM.chapter)
    
    result = await db.execute(stmt)
    rows = result.fetchall()
    
    print(f"   Found {len(rows)} chapters")
    for row in rows:
        print(f"   - {row[0]} ({row[2]} topics)")
    
    chapters = [
        ChapterResponse(
            chapter=row[0],
            subject=row[1],
            topic_count=row[2],
            topics=[t.strip() for t in (row[3] or "").split(",") if t.strip()]
        )
        for row in rows
    ]
    
    print(f"   Returning {len(chapters)} chapters\n")
    
    return ChaptersResponse(
        grade=grade,
        chapters=chapters,
    )
