"""Translation pull request model for PR Guardian."""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class PRState(str, Enum):
    """Pull request state."""

    OPEN = "open"
    CLOSED = "closed"
    MERGED = "merged"


class TranslationPullRequest(BaseModel):
    """Represents a discovered translation PR."""

    owner: str = Field(..., min_length=1, description="Repository owner")
    repo_name: str = Field(..., min_length=1, description="Repository name")
    number: int = Field(..., gt=0, description="PR number")
    title: str = Field(..., min_length=1, description="PR title")
    url: str = Field(..., description="PR URL")
    state: PRState = Field(..., description="PR state")
    source_branch: str = Field(..., min_length=1, description="Source branch name")
    target_branch: str = Field(..., min_length=1, description="Target branch name")
    created_at: datetime = Field(..., description="PR creation timestamp (UTC)")
    updated_at: datetime = Field(..., description="PR last update timestamp (UTC)")
    author: str = Field(..., min_length=1, description="PR author username")
    translation_files: list[str] = Field(
        default_factory=list, description="Translation files modified in PR"
    )
    comment_count: int = Field(default=0, ge=0, description="Number of comments on PR")
    processed_at: Optional[datetime] = Field(
        default=None, description="Timestamp when agent processed this PR"
    )

    @field_validator("created_at", "updated_at", "processed_at")
    @classmethod
    def ensure_utc(cls, v: Optional[datetime]) -> Optional[datetime]:
        """Ensure datetime is UTC timezone-aware."""
        if v is None:
            return v
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate GitHub PR URL format."""
        if not v.startswith("https://github.com/"):
            raise ValueError(f"Invalid GitHub PR URL: {v}")
        return v

    @property
    def is_open(self) -> bool:
        """Check if PR is open."""
        return self.state == PRState.OPEN

    @property
    def has_translation_files(self) -> bool:
        """Check if PR has translation files."""
        return len(self.translation_files) > 0
