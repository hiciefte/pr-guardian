"""Session report model for PR Guardian."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class LLMStats(BaseModel):
    """LLM usage statistics for a session."""

    tokens_in: int = Field(default=0, ge=0, description="Input tokens used")
    tokens_out: int = Field(default=0, ge=0, description="Output tokens generated")
    cost_estimate: float = Field(default=0.0, ge=0.0, description="Estimated cost in USD")
    cache_hits: int = Field(default=0, ge=0, description="Number of cache hits")
    requests: int = Field(default=0, ge=0, description="Total API requests")


class SessionReport(BaseModel):
    """Represents an execution session report."""

    session_id: str = Field(
        default_factory=lambda: f"session_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}",
        description="Unique session identifier",
    )
    start_time: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Session start timestamp (UTC)",
    )
    end_time: Optional[datetime] = Field(
        default=None, description="Session end timestamp (UTC)"
    )
    duration_seconds: Optional[float] = Field(
        default=None, description="Execution duration in seconds"
    )
    repositories_processed: list[str] = Field(
        default_factory=list, description="Repository identifiers processed"
    )
    prs_discovered: int = Field(default=0, ge=0, description="Total PRs discovered")
    prs_processed: int = Field(default=0, ge=0, description="PRs successfully processed")
    prs_skipped: int = Field(default=0, ge=0, description="PRs skipped")
    prs_failed: int = Field(default=0, ge=0, description="PRs failed during processing")
    comments_retrieved: int = Field(default=0, ge=0, description="Total comments retrieved")
    comments_classified: int = Field(default=0, ge=0, description="Comments classified")
    comments_by_type: dict[str, int] = Field(
        default_factory=lambda: {
            "Critical": 0,
            "Constructive": 0,
            "Nitpick": 0,
            "Question": 0,
            "Praise": 0,
        },
        description="Comment counts by classification type",
    )
    changes_implemented: int = Field(default=0, ge=0, description="Translation changes implemented")
    commits_created: int = Field(default=0, ge=0, description="Commits created and pushed")
    feedback_issues_created: int = Field(default=0, ge=0, description="Feedback issues filed")
    errors: list[str] = Field(default_factory=list, description="Error messages encountered")
    llm_stats: LLMStats = Field(
        default_factory=LLMStats, description="LLM usage statistics"
    )
    success: bool = Field(default=True, description="Overall session success status")

    @field_validator("start_time", "end_time")
    @classmethod
    def ensure_utc(cls, v: Optional[datetime]) -> Optional[datetime]:
        """Ensure datetime is UTC timezone-aware."""
        if v is None:
            return v
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)

    @model_validator(mode="after")
    def validate_pr_counts(self) -> "SessionReport":
        """Validate PR counts are consistent."""
        total = self.prs_processed + self.prs_skipped + self.prs_failed
        if total > 0 and total != self.prs_discovered:
            raise ValueError(
                f"PR counts inconsistent: {total} != {self.prs_discovered}"
            )
        return self

    @model_validator(mode="after")
    def validate_end_time(self) -> "SessionReport":
        """Validate end time is after start time."""
        if self.end_time and self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self

    def complete(self) -> None:
        """Mark session as complete and calculate duration."""
        self.end_time = datetime.now(timezone.utc)
        self.duration_seconds = (self.end_time - self.start_time).total_seconds()
        self.success = self._calculate_success()

    def _calculate_success(self) -> bool:
        """Determine if session was successful."""
        # Critical errors fail the session
        if any("CRITICAL" in err or "FATAL" in err for err in self.errors):
            return False

        # No PRs processed when discovered is a failure
        if self.prs_discovered > 0 and self.prs_processed == 0:
            return False

        # Changes without commits is a failure
        if self.changes_implemented > 0 and self.commits_created == 0:
            return False

        # All PRs failed is a failure
        if self.prs_failed == self.prs_discovered and self.prs_discovered > 0:
            return False

        return True

    def add_error(self, error: str) -> None:
        """Add an error message to the session."""
        self.errors.append(error)

    def increment_comments(self, classification_type: str) -> None:
        """Increment comment count for a classification type."""
        if classification_type in self.comments_by_type:
            self.comments_by_type[classification_type] += 1
            self.comments_classified += 1
