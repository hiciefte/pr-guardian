"""Translation change model for PR Guardian."""

import re
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class ChangeType(str, Enum):
    """Type of translation change."""

    FIX = "fix"
    REFINEMENT = "refinement"
    UPDATE = "update"


def extract_placeholders(text: str) -> set[str]:
    """Extract placeholder variables from translation text.

    Supports formats: {variable}, %s, %d, {{key}}, $variable, %(name)s
    """
    patterns = [
        r"\{[^}]+\}",        # {variable}
        r"%[sd]",            # %s, %d
        r"\{\{[^}]+\}\}",    # {{key}}
        r"\$\w+",            # $variable
        r"%\([^)]+\)s",      # %(name)s
    ]
    placeholders: set[str] = set()
    for pattern in patterns:
        placeholders.update(re.findall(pattern, text))
    return placeholders


class TranslationChange(BaseModel):
    """Represents a specific translation modification."""

    file_path: str = Field(..., description="Translation file path")
    translation_key: str = Field(..., min_length=1, description="Translation key")
    original_value: str = Field(..., min_length=1, description="Original translation text")
    new_value: str = Field(..., min_length=1, description="Modified translation text")
    locale: str = Field(..., description="Locale identifier (xx_XX format)")
    change_type: ChangeType = Field(..., description="Type of change")
    comment_id: int = Field(..., gt=0, description="Source CodeRabbitAI comment ID")
    line_start: Optional[int] = Field(default=None, gt=0, description="Starting line number")
    line_end: Optional[int] = Field(default=None, gt=0, description="Ending line number")
    validated: bool = Field(default=False, description="Whether syntax validation passed")
    validation_error: Optional[str] = Field(
        default=None, description="Validation error message"
    )

    @field_validator("locale")
    @classmethod
    def validate_locale(cls, v: str) -> str:
        """Validate locale format (xx_XX)."""
        if not re.match(r"^[a-z]{2}_[A-Z]{2}$", v):
            raise ValueError(f"Invalid locale format: {v} (expected: xx_XX)")
        return v

    @model_validator(mode="after")
    def validate_values_different(self) -> "TranslationChange":
        """Ensure original and new values are different."""
        if self.original_value == self.new_value:
            raise ValueError("new_value must differ from original_value")
        return self

    @model_validator(mode="after")
    def validate_line_numbers(self) -> "TranslationChange":
        """Validate line number range."""
        if self.line_start and self.line_end:
            if self.line_end < self.line_start:
                raise ValueError(
                    f"line_end ({self.line_end}) < line_start ({self.line_start})"
                )
        return self

    @property
    def original_placeholders(self) -> set[str]:
        """Extract placeholders from original value."""
        return extract_placeholders(self.original_value)

    @property
    def new_placeholders(self) -> set[str]:
        """Extract placeholders from new value."""
        return extract_placeholders(self.new_value)

    @property
    def placeholders_preserved(self) -> bool:
        """Check if all placeholders are preserved in the change."""
        return self.original_placeholders == self.new_placeholders

    @property
    def file_extension(self) -> str:
        """Get the file extension."""
        return Path(self.file_path).suffix

    def validate_placeholders(self) -> tuple[bool, str]:
        """Validate placeholder integrity between original and new values."""
        if not self.placeholders_preserved:
            missing = self.original_placeholders - self.new_placeholders
            added = self.new_placeholders - self.original_placeholders
            errors = []
            if missing:
                errors.append(f"Missing placeholders: {missing}")
            if added:
                errors.append(f"Added placeholders: {added}")
            return False, "; ".join(errors)
        return True, ""
