"""Translation extraction model for LLM-based comment parsing."""

import re
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class ImplementationDecision(str, Enum):
    """Implementation decision based on confidence."""

    IMPLEMENT = "implement"
    HUMAN_REVIEW = "human_review"
    SKIP = "skip"


class TranslationExtraction(BaseModel):
    """Represents LLM-extracted translation change from a comment."""

    translation_key: str = Field(..., min_length=1, description="Translation key being changed")
    original_value: str = Field(..., min_length=1, description="Current translation text")
    new_value: str = Field(..., min_length=1, description="Suggested replacement text")
    locale: str = Field(..., description="Language locale (xx_XX format)")
    reasoning: str = Field(..., min_length=1, description="Why the change is suggested")
    confidence: float = Field(..., ge=0.0, le=1.0, description="LLM extraction confidence")
    comment_id: int = Field(..., gt=0, description="Source comment ID")
    extracted_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Extraction timestamp (UTC)",
    )
    llm_model: str = Field(
        default="claude-3-haiku-20240307", description="LLM model used"
    )
    implementation_decision: Optional[ImplementationDecision] = Field(
        default=None, description="Auto-decision based on confidence"
    )

    @field_validator("locale")
    @classmethod
    def validate_locale(cls, v: str) -> str:
        """Validate locale format (xx_XX)."""
        if not re.match(r"^[a-z]{2}_[A-Z]{2}$", v):
            raise ValueError(f"Invalid locale format: {v} (expected: xx_XX)")
        return v

    @field_validator("extracted_at")
    @classmethod
    def ensure_utc(cls, v: datetime) -> datetime:
        """Ensure datetime is UTC timezone-aware."""
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)

    @model_validator(mode="after")
    def validate_values_different(self) -> "TranslationExtraction":
        """Ensure original and new values are different."""
        if self.original_value == self.new_value:
            raise ValueError("new_value must differ from original_value")
        return self

    @model_validator(mode="after")
    def set_implementation_decision(self) -> "TranslationExtraction":
        """Auto-set implementation decision based on confidence if not provided."""
        if self.implementation_decision is None:
            if self.confidence >= 0.80:
                self.implementation_decision = ImplementationDecision.IMPLEMENT
            elif self.confidence >= 0.60:
                self.implementation_decision = ImplementationDecision.HUMAN_REVIEW
            else:
                self.implementation_decision = ImplementationDecision.SKIP
        return self

    @property
    def should_implement(self) -> bool:
        """Check if extraction should be auto-implemented."""
        return self.implementation_decision == ImplementationDecision.IMPLEMENT

    @property
    def needs_review(self) -> bool:
        """Check if extraction needs human review."""
        return self.implementation_decision == ImplementationDecision.HUMAN_REVIEW
