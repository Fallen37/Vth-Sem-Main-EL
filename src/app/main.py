"""FastAPI application entry point."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse

from config.settings import get_settings
from src.models.database import init_db

settings = get_settings()

# Path to frontend build directory
FRONTEND_DIR = Path(__file__).parent.parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown."""
    # Startup: Initialize database
    await init_db()
    yield
    # Shutdown: cleanup if needed


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered science tutor for autistic students using RAG",
    lifespan=lifespan,
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lazy import routers to speed up startup
def _load_routers():
    """Lazy load routers to defer heavy imports."""
    from src.api import (
        auth_router,
        chat_router,
        profile_router,
        content_router,
        progress_router,
        guardian_router,
        calm_router,
        websocket_router,
    )
    
    app.include_router(auth_router)
    app.include_router(chat_router)
    app.include_router(profile_router)
    app.include_router(content_router)
    app.include_router(progress_router)
    app.include_router(guardian_router)
    app.include_router(calm_router)
    app.include_router(websocket_router)

# Load routers after app creation
_load_routers()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": settings.app_version}


@app.get("/api")
async def api_info():
    """API information endpoint."""
    return {
        "message": f"Welcome to {settings.app_name} API",
        "version": settings.app_version,
        "docs": "/docs",
    }


# Serve frontend static files if the build exists
if FRONTEND_DIR.exists():
    # Mount static assets (JS, CSS, images)
    assets_dir = FRONTEND_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
    
    # Serve vite.svg if it exists
    vite_svg = FRONTEND_DIR / "vite.svg"
    if vite_svg.exists():
        @app.get("/vite.svg")
        async def serve_vite_svg():
            return FileResponse(vite_svg)
    
    # Catch-all route for SPA - must be last!
    @app.get("/")
    @app.get("/login")
    @app.get("/register")
    @app.get("/dashboard")
    @app.get("/chat")
    @app.get("/profile-setup")
    @app.get("/progress")
    @app.get("/settings")
    @app.get("/calm")
    @app.get("/guardian")
    @app.get("/materials")
    async def serve_spa():
        """Serve the React SPA for frontend routes."""
        index_path = FRONTEND_DIR / "index.html"
        if index_path.exists():
            return FileResponse(index_path, media_type="text/html")
        return HTMLResponse("<h1>Frontend not built</h1>", status_code=404)

else:
    @app.get("/")
    async def root():
        """Root endpoint when frontend is not built."""
        return {
            "message": f"Welcome to {settings.app_name}",
            "version": settings.app_version,
            "note": "Frontend not built. Run 'cd frontend && npm run build' to enable the web interface.",
            "docs": "/docs",
        }
