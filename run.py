#!/usr/bin/env python
"""
Run the Autism Science Tutor application.

This script starts the FastAPI server which serves both:
- The REST API backend
- The React frontend (from frontend/dist/)

Usage:
    python run.py
    
Then open http://localhost:8080 in your browser.
"""

import uvicorn
import sys

if __name__ == "__main__":
    print("🌟 Starting Autism Science Tutor...")
    print("📍 Open http://localhost:8080 in your browser")
    print("📚 API docs available at http://localhost:8080/docs")
    print("-" * 50)
    
    # Disable reload in production for faster startup
    reload = "--reload" in sys.argv
    
    uvicorn.run(
        "src.app.main:app",
        host="127.0.0.1",
        port=8080,
        reload=reload,
        log_level="info",
    )
