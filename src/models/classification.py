"""Comment classification model for PR Guardian."""

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


class ClassificationType(str, Enum):
    """Comment classification categories."""

    CRITICAL = "Critical"
    CONSTRUCTIVE = "Constructive"
    NITPICK = "Nitpick"
    QUESTION = "Question"
    PRAISE = "Praise"


class ImplementationDecision(str, Enum):
    """Implementation decision for classified comments."""

    IMPLEMENT = "implement"
    SKIP = "skip"
    CLARIFY = "clarify"


class CommentClassification(BaseModel):
    """Represents agent's classification of a review comment."""

    comment_id: int = Field(..., gt=0, description="Associated comment ID")
    type: ClassificationType = Field(..., description="Classification category")
    priority: Literal[1, 2, 3] = Field(..., description="Implementation priority (1=highest)")
    should_implement: bool = Field(..., description="Whether to implement this comment")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Classification confidence")
    reasoning: str = Field(..., min_length=1, description="Explanation of classification")
    skip_reason: Optional[str] = Field(
        default=None, description="Reason for skipping implementation"
    )
    pattern_tags: list[str] = Field(
        default_factory=list, description="Tags for pattern recognition"
    )
    affected_locales: list[str] = Field(
        default_factory=list, description="Locales impacted by this comment"
    )
    requires_human_review: bool = Field(
        default=False, description="Whether human review is needed"
    )
    glossary_conflict: bool = Field(
        default=False, description="Whether conflicts with glossary"
    )

    @model_validator(mode="after")
    def validate_priority_matches_type(self) -> "CommentClassification":
        """Validate that priority matches classification type."""
        priority_map = {
            ClassificationType.CRITICAL: 1,
            ClassificationType.CONSTRUCTIVE: 2,
            ClassificationType.NITPICK: 3,
            ClassificationType.QUESTION: 3,
            ClassificationType.PRAISE: 3,
        }
        expected = priority_map.get(self.type)
        if expected and self.priority != expected:
            raise ValueError(
                f"Priority {self.priority} does not match type {self.type} (expected {expected})"
            )
        return self

    @model_validator(mode="after")
    def validate_skip_logic(self) -> "CommentClassification":
        """Validate skip reason is provided when not implementing."""
        if not self.should_implement and not self.skip_reason:
            raise ValueError("skip_reason required when should_implement is False")
        if self.glossary_conflict and self.should_implement:
            raise ValueError("Glossary conflicts should result in skip decision")
        return self

    @property
    def is_actionable(self) -> bool:
        """Check if classification requires action."""
        return self.type in (
            ClassificationType.CRITICAL,
            ClassificationType.CONSTRUCTIVE,
            ClassificationType.NITPICK,
        )

    @property
    def needs_response(self) -> bool:
        """Check if classification needs a response (not implementation)."""
        return self.type in (ClassificationType.QUESTION, ClassificationType.PRAISE)
