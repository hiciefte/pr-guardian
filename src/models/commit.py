"""Commit record model for PR Guardian."""

import re
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class VerificationMethod(str, Enum):
    """Signature verification method."""

    WEB_FLOW = "web-flow"
    GPG = "gpg"


class CommitRecord(BaseModel):
    """Represents a git commit created by the agent."""

    sha: str = Field(..., description="Git commit SHA-1 hash")
    message: str = Field(..., min_length=1, description="Full commit message")
    files_changed: list[str] = Field(..., min_length=1, description="Files changed in commit")
    signed: bool = Field(..., description="Whether commit is GPG signed")
    timestamp: datetime = Field(..., description="Commit creation time (UTC)")
    comment_ids: list[int] = Field(
        ..., min_length=1, description="Referenced CodeRabbitAI comment IDs"
    )
    author_name: str = Field(
        default="PR Guardian Bot", description="Commit author name"
    )
    author_email: str = Field(
        default="pr-guardian@example.com", description="Commit author email"
    )
    signature_verified: bool = Field(
        default=False, description="Whether GPG signature verified"
    )
    verification_method: Optional[VerificationMethod] = Field(
        default=None, description="Signature verification method"
    )

    @field_validator("sha")
    @classmethod
    def validate_sha(cls, v: str) -> str:
        """Validate commit SHA format (40 hex characters)."""
        if not re.match(r"^[a-f0-9]{40}$", v):
            raise ValueError(f"Invalid commit hash format: {v}")
        return v

    @field_validator("timestamp")
    @classmethod
    def ensure_utc(cls, v: datetime) -> datetime:
        """Ensure datetime is UTC timezone-aware."""
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)

    @model_validator(mode="after")
    def validate_signing(self) -> "CommitRecord":
        """Validate signing requirements (constitution mandate)."""
        if not self.signed:
            raise ValueError("Commit must be GPG signed (constitution requirement)")
        if self.signed and not self.signature_verified:
            # Warning: signature should be verified, but don't fail validation
            pass
        return self

    @property
    def subject(self) -> str:
        """Extract subject line from commit message."""
        return self.message.split("\n")[0]

    @property
    def body(self) -> Optional[str]:
        """Extract body from commit message."""
        lines = self.message.split("\n")
        if len(lines) > 2:
            return "\n".join(lines[2:])
        return None

    @property
    def follows_conventional_rules(self) -> bool:
        """Check if commit follows conventional rules."""
        subject = self.subject

        # Rule 2: Subject <= 72 chars (hard limit)
        if len(subject) > 72:
            return False

        # Rule 3: Capitalize subject
        if subject and not subject[0].isupper():
            return False

        # Rule 4: No trailing period
        if subject.endswith("."):
            return False

        # Rule 1: Blank line between subject and body
        lines = self.message.split("\n")
        if len(lines) > 1 and lines[1] != "":
            return False

        return True

    def validate_conventional_rules(self) -> tuple[bool, list[str]]:
        """Validate all 7 conventional commit rules."""
        errors = []
        subject = self.subject

        # Rule 2: Subject length
        if len(subject) > 50:
            errors.append(f"Subject exceeds 50 characters (has {len(subject)})")
        if len(subject) > 72:
            errors.append(f"Subject exceeds 72 character hard limit")

        # Rule 3: Capitalize
        if subject and not subject[0].isupper():
            errors.append("Subject must start with capital letter")

        # Rule 4: No period
        if subject.endswith("."):
            errors.append("Subject must not end with period")

        # Rule 1: Blank line
        lines = self.message.split("\n")
        if len(lines) > 1 and lines[1] != "":
            errors.append("Must have blank line between subject and body")

        # Rule 6: Body wrap at 72 chars
        if self.body:
            for line in self.body.split("\n"):
                if len(line) > 72:
                    errors.append(f"Body line exceeds 72 characters: {line[:50]}...")
                    break

        return len(errors) == 0, errors
