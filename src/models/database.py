"""Database connection and session management."""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text

from config.settings import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""

    pass


async def get_db() -> AsyncSession:
    """Dependency for getting database sessions."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database tables and run lightweight migrations.

    This keeps the SQLite schema in sync with our SQLAlchemy models
    without requiring a full migration framework.
    """
    # Import models locally so their tables are registered with Base.metadata
    # without creating circular imports at module import time.
    from src.models import (
        user,  # noqa: F401
        learning_profile,  # noqa: F401
        session,  # noqa: F401
        document,  # noqa: F401
        progress,  # noqa: F401
        response_storage,  # noqa: F401
        analyzed_response,  # noqa: F401
    )

    async with engine.begin() as conn:
        # Create any missing tables that are registered on Base.metadata
        await conn.run_sync(Base.metadata.create_all)

        # --- Lightweight migrations for existing deployments ---
        # 1) Ensure `blocks` column exists on `stored_responses`
        try:
            result = await conn.execute(text("PRAGMA table_info('stored_responses')"))
            columns = [row[1] for row in result.fetchall()]
            if "blocks" not in columns:
                await conn.execute(text("ALTER TABLE stored_responses ADD COLUMN blocks TEXT"))
        except Exception:
            # Best-effort migration; don't block app startup
            pass
