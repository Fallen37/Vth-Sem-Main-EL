"""API routes package for the Autism Science Tutor application."""

from src.api.auth import router as auth_router
from src.api.chat import router as chat_router
from src.api.profile import router as profile_router
from src.api.content import router as content_router
from src.api.progress import router as progress_router
from src.api.guardian import router as guardian_router
from src.api.calm import router as calm_router
from src.api.websocket import router as websocket_router

__all__ = [
    "auth_router",
    "chat_router",
    "profile_router",
    "content_router",
    "progress_router",
    "guardian_router",
    "calm_router",
    "websocket_router",
]
