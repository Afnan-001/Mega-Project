"""
server/models/user.py — User ODM document for authentication and RBAC.
"""
from __future__ import annotations

from datetime import datetime, timezone
from beanie import Document, Indexed
from pydantic import Field


class UserDocument(Document):
    """User account document with role ('teacher' or 'student')."""

    email: Indexed(str, unique=True)
    hashed_password: str
    full_name: str
    role: str = "student"  # 'teacher' | 'student'
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "users"
