"""API dependencies for dependency injection."""

from typing import AsyncGenerator, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.database import get_db
from src.models.user import UserORM
from src.models.enums import UserRole
from sqlalchemy import select


# Simple bearer token security (in production, use proper JWT)
security = HTTPBearer(auto_error=False)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session."""
    async for session in get_db():
        yield session


async def get_current_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[UUID]:
    """
    Extract user ID from authorization header.
    
    In production, this would validate a JWT token.
    For now, we accept the user ID directly in the token.
    """
    if not credentials:
        return None
    
    try:
        # Simple implementation: token is the user ID
        return UUID(credentials.credentials)
    except ValueError:
        return None


async def get_current_user(
    user_id: Optional[UUID] = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
) -> Optional[UserORM]:
    """Get current user from database."""
    if not user_id:
        return None
    
    result = await db.execute(
        select(UserORM).where(UserORM.id == str(user_id))
    )
    return result.scalar_one_or_none()


async def require_current_user(
    user: Optional[UserORM] = Depends(get_current_user),
) -> UserORM:
    """Require authenticated user."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def require_student(
    user: UserORM = Depends(require_current_user),
) -> UserORM:
    """Require authenticated student."""
    if user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student access required",
        )
    return user


async def require_guardian(
    user: UserORM = Depends(require_current_user),
) -> UserORM:
    """Require authenticated guardian."""
    if user.role != UserRole.GUARDIAN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Guardian access required",
        )
    return user


async def require_admin(
    user: UserORM = Depends(require_current_user),
) -> UserORM:
    """Require authenticated admin."""
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user
