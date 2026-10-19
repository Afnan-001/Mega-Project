"""
server/config.py — Centralized configuration loaded from environment / .env file.
"""
from __future__ import annotations

from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings populated from environment variables or a .env file."""

    # ── MongoDB ──────────────────────────────────────────────────────
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "mega_project"

    # ── JWT Authentication ───────────────────────────────────────────
    JWT_SECRET_KEY: str = "change-me-in-production-use-a-long-random-string"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # ── Pipeline Paths ───────────────────────────────────────────────
    PROJECT_ROOT: Path = Path(__file__).resolve().parents[1]
    MAIN_DIR: Path = PROJECT_ROOT / "Main"
    BOOKS_DIR: Path = MAIN_DIR / "books"
    COURSE_OUTPUTS_DIR: Path = MAIN_DIR / "outputs" / "courses"

    # ── CORS ─────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["*"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # ignore unexpected env vars


# Singleton instance used across the application
settings = Settings()
