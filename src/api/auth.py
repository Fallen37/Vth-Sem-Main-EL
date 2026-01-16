"""Authentication API endpoints."""

from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db_session, require_current_user
from src.models.user import UserORM, User, UserCreate
from src.models.enums import UserRole, Syllabus


router = APIRouter(prefix="/auth", tags=["Authentication"])


class RegisterRequest(BaseModel):
    """Request model for user registration."""
    
    email: EmailStr
    name: str = Field(min_length=1, max_length=100)
    role: UserRole = UserRole.STUDENT
    grade: Optional[int] = Field(None, ge=5, le=10)
    syllabus: Optional[Syllabus] = None


class LoginRequest(BaseModel):
    """Request model for login."""
    
    email: EmailStr


class AuthResponse(BaseModel):
    """Response model for authentication."""
    
    user_id: UUID
    token: str
    user: dict


class UserResponse(BaseModel):
    """Response model for user data."""
    
    id: UUID
    email: str
    name: str
    role: UserRole
    grade: Optional[int] = None
    syllabus: Optional[str] = None


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db_session),
) -> AuthResponse:
    """
    Register a new user.
    
    Returns a token (user ID) for authentication.
    """
    # Check if email already exists
    result = await db.execute(
        select(UserORM).where(UserORM.email == request.email)
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    # Validate student-specific fields
    if request.role == UserRole.STUDENT:
        if request.grade is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Grade is required for students",
            )
        if request.syllabus is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Syllabus is required for students",
            )
    
    # Create user
    user_id = str(uuid4())
    user = UserORM(
        id=user_id,
        email=request.email,
        name=request.name,
        role=request.role,
        grade=request.grade if request.role == UserRole.STUDENT else None,
        syllabus=request.syllabus.value if request.syllabus and request.role == UserRole.STUDENT else None,
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return AuthResponse(
        user_id=UUID(user_id),
        token=user_id,  # Simple token = user ID
        user={
            "id": user_id,
            "email": user.email,
            "name": user.name,
            "role": user.role.value,
            "grade": user.grade,
            "syllabus": user.syllabus,
        },
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db_session),
) -> AuthResponse:
    """
    Login with email.
    
    Returns a token (user ID) for authentication.
    In production, this would validate credentials properly.
    """
    result = await db.execute(
        select(UserORM).where(UserORM.email == request.email)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    
    return AuthResponse(
        user_id=UUID(user.id),
        token=user.id,  # Simple token = user ID
        user={
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role.value,
            "grade": user.grade,
            "syllabus": user.syllabus,
        },
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    user: UserORM = Depends(require_current_user),
) -> UserResponse:
    """Get current user information."""
    return UserResponse(
        id=UUID(user.id),
        email=user.email,
        name=user.name,
        role=user.role,
        grade=user.grade,
        syllabus=user.syllabus,
    )
