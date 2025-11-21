"""Feedback issue model for PR Guardian."""

import re
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class FeedbackIssue(BaseModel):
    """Represents a GitHub issue created for feedback."""

    issue_number: int = Field(..., gt=0, description="GitHub issue number")
    url: str = Field(..., description="GitHub issue URL")
    title: str = Field(..., min_length=1, max_length=100, description="Issue title")
    body: str = Field(..., min_length=1, description="Issue body (markdown)")
    target_repository: str = Field(
        ..., description="Feedback repository identifier (owner/repo)"
    )
    created_at: datetime = Field(..., description="Issue creation timestamp (UTC)")
    session_id: str = Field(..., description="Session that created this issue")
    pattern_types: list[str] = Field(
        ..., min_length=1, description="Pattern types included in issue"
    )
    labels: list[str] = Field(
        default_factory=lambda: ["translation-feedback", "automated", "pr-guardian"],
        description="GitHub issue labels",
    )

    @field_validator("target_repository")
    @classmethod
    def validate_repository(cls, v: str) -> str:
        """Validate repository format."""
        if not re.match(r"^[a-zA-Z0-9-]+/[a-zA-Z0-9._-]+$", v):
            raise ValueError(f"Invalid repository format: {v}")
        return v

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate GitHub issue URL format."""
        if not v.startswith("https://github.com/"):
            raise ValueError(f"Invalid GitHub issue URL: {v}")
        return v

    @field_validator("created_at")
    @classmethod
    def ensure_utc(cls, v: datetime) -> datetime:
        """Ensure datetime is UTC timezone-aware."""
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)

    @property
    def short_url(self) -> str:
        """Get shortened issue URL (repo#number format)."""
        return f"{self.target_repository}#{self.issue_number}"
