"""Application settings and environment configuration."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "Autism Science Tutor"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: Literal["development", "staging", "production"] = "development"

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/tutor.db"

    # ChromaDB
    chroma_persist_directory: str = "./data/chroma"
    chroma_collection_name: str = "curriculum_content"

    # Google Gemini API
    google_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    # Sentence Transformers (local embeddings)
    embedding_model_name: str = "all-MiniLM-L6-v2"
    use_local_embeddings: bool = True

    # RAG Configuration
    rag_similarity_threshold: float = 0.7
    rag_top_k: int = 5
    rag_confidence_threshold: float = 0.6

    # Session
    session_timeout_minutes: int = 60

    # Progress
    review_comprehension_threshold: float = 0.6


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
