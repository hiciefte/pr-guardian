"""Repository target model for PR Guardian."""

import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator


DEFAULT_TRANSLATION_PATTERNS: list[str] = [
    "*.properties",
    "**/i18n/**/*.json",
    "**/locales/**/*.yml",
    "**/locales/**/*.yaml",
    "**/lang/**/*",
]


class RepositoryTarget(BaseModel):
    """Represents a GitHub repository to monitor."""

    owner: str = Field(..., description="GitHub repository owner")
    repository: str = Field(..., description="GitHub repository name")
    branch_filter: Optional[str] = Field(
        default=None, description="Only process PRs targeting this branch"
    )
    translation_file_patterns: list[str] = Field(
        default_factory=lambda: DEFAULT_TRANSLATION_PATTERNS.copy(),
        description="Translation file glob patterns",
    )
    enabled: bool = Field(default=True, description="Whether to process this repository")

    @field_validator("owner")
    @classmethod
    def validate_owner(cls, v: str) -> str:
        """Validate GitHub owner format."""
        if not re.match(r"^[a-zA-Z0-9-]+$", v):
            raise ValueError(f"Invalid owner format: {v}")
        return v

    @field_validator("repository")
    @classmethod
    def validate_repository(cls, v: str) -> str:
        """Validate GitHub repository name format."""
        if not re.match(r"^[a-zA-Z0-9._-]+$", v):
            raise ValueError(f"Invalid repository name: {v}")
        return v

    @property
    def full_name(self) -> str:
        """Return owner/repository format."""
        return f"{self.owner}/{self.repository}"
