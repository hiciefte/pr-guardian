"""Review comment model for PR Guardian."""

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ReviewComment(BaseModel):
    """Represents a CodeRabbitAI review comment."""

    id: int = Field(..., gt=0, description="GitHub comment ID")
    body: str = Field(..., min_length=1, description="Comment body text")
    author: str = Field(..., min_length=1, description="Comment author username")
    created_at: datetime = Field(..., description="Comment creation timestamp (UTC)")
    url: str = Field(..., description="Comment URL")
    file_path: Optional[str] = Field(
        default=None, description="File path for review comments"
    )
    line_number: Optional[int] = Field(
        default=None, gt=0, description="Line number in file"
    )
    diff_hunk: Optional[str] = Field(
        default=None, description="Diff context around comment"
    )
    conventional_label: Optional[str] = Field(
        default=None, description="CodeRabbitAI's label (nitpick, suggestion, etc.)"
    )

    @field_validator("created_at")
    @classmethod
    def ensure_utc(cls, v: datetime) -> datetime:
        """Ensure datetime is UTC timezone-aware."""
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)

    @field_validator("author")
    @classmethod
    def validate_author(cls, v: str) -> str:
        """Validate comment author (expected to be coderabbitai for processing)."""
        return v.lower()

    @property
    def is_coderabbitai(self) -> bool:
        """Check if comment is from CodeRabbitAI."""
        return self.author == "coderabbitai"

    @property
    def is_review_comment(self) -> bool:
        """Check if this is a file-specific review comment."""
        return self.file_path is not None
