"""Feedback pattern model for PR Guardian."""

from enum import Enum

from pydantic import BaseModel, Field, field_validator


class PatternType(str, Enum):
    """Type of feedback pattern."""

    TERMINOLOGY = "terminology"
    PUNCTUATION = "punctuation"
    FORMALITY = "formality"
    GRAMMAR = "grammar"
    PLACEHOLDER = "placeholder"
    CULTURAL = "cultural"


class PatternSeverity(str, Enum):
    """Severity level of feedback pattern."""

    CRITICAL = "critical"
    MODERATE = "moderate"
    MINOR = "minor"


class FeedbackPattern(BaseModel):
    """Represents aggregated feedback insights from a session."""

    pattern_type: PatternType = Field(..., description="Type of feedback pattern")
    frequency: int = Field(..., gt=0, description="Number of occurrences in session")
    affected_locales: list[str] = Field(
        ..., min_length=1, description="Locales where pattern appears"
    )
    examples: list[str] = Field(
        ..., min_length=1, max_length=5, description="Specific example comments"
    )
    severity: PatternSeverity = Field(..., description="Pattern severity level")
    recommendations: list[str] = Field(
        ..., min_length=1, description="Suggested improvement actions"
    )
    session_id: str = Field(..., description="Session where pattern identified")
    automated_fix_possible: bool = Field(
        default=False, description="Whether can be automated"
    )

    @field_validator("affected_locales")
    @classmethod
    def validate_locales(cls, v: list[str]) -> list[str]:
        """Validate locale formats."""
        import re
        for locale in v:
            if not re.match(r"^[a-z]{2}_[A-Z]{2}$", locale):
                raise ValueError(f"Invalid locale format: {locale}")
        return v

    @property
    def is_high_priority(self) -> bool:
        """Check if pattern is high priority (critical or high frequency)."""
        return self.severity == PatternSeverity.CRITICAL or self.frequency >= 5

    @property
    def primary_recommendation(self) -> str:
        """Get the primary recommendation."""
        return self.recommendations[0] if self.recommendations else ""
