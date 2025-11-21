"""PR Guardian configuration model."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from .repository import RepositoryTarget


class LogLevel(str, Enum):
    """Logging verbosity levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class SigningMethod(str, Enum):
    """Commit signing method."""

    WEB_FLOW = "web-flow"
    GPG = "gpg"


class GitHubSettings(BaseModel):
    """GitHub authentication and target settings."""

    token_env: str = Field(
        default="GITHUB_TOKEN",
        description="Environment variable name for GitHub token",
    )
    target_username: str = Field(
        ..., description="GitHub username to monitor for PRs"
    )

    @field_validator("target_username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate GitHub username format."""
        if not v or not v.strip():
            raise ValueError("target_username cannot be empty")
        return v.strip()


class FeedbackSettings(BaseModel):
    """Feedback repository settings."""

    repository: Optional[str] = Field(
        default=None, description="Repository for feedback issues (owner/repo)"
    )
    labels: list[str] = Field(
        default_factory=lambda: ["translation-feedback", "automated", "pr-guardian"],
        description="Labels to apply to feedback issues",
    )

    @field_validator("repository")
    @classmethod
    def validate_repository(cls, v: Optional[str]) -> Optional[str]:
        """Validate repository format."""
        if v is None:
            return None
        value = v.strip()
        if "/" not in value:
            raise ValueError("Invalid repository format (expected: owner/repository)")
        return value


class ExecutionSettings(BaseModel):
    """Execution and scheduling settings."""

    max_comments_per_pr: int = Field(
        default=50, ge=1, le=100, description="Maximum comments to process per PR"
    )
    timeout_seconds: int = Field(
        default=1800, ge=60, le=3600, description="Maximum execution time in seconds"
    )
    schedule_cron: str = Field(
        default="0 2 * * *", description="Cron expression for execution schedule"
    )


class SigningConfig(BaseModel):
    """Commit signing configuration."""

    method: SigningMethod = Field(
        default=SigningMethod.WEB_FLOW, description="Signing method"
    )
    gpg_key_path: Optional[str] = Field(
        default=None, description="Path to GPG private key"
    )
    deploy_key_path: Optional[str] = Field(
        default=None, description="Path to SSH deploy key"
    )


class LoggingSettings(BaseModel):
    """Logging configuration."""

    level: LogLevel = Field(default=LogLevel.INFO, description="Logging verbosity")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string",
    )


class LLMSettings(BaseModel):
    """LLM configuration for comment parsing."""

    api_key_env: str = Field(
        default="ANTHROPIC_API_KEY",
        description="Environment variable for Anthropic API key",
    )
    model: str = Field(
        default="claude-3-5-haiku-20241022",
        description="LLM model for comment parsing",
    )
    max_tokens: int = Field(
        default=1024, ge=100, le=4096, description="Maximum tokens per response"
    )
    confidence_threshold: float = Field(
        default=0.80, ge=0.0, le=1.0, description="Minimum confidence for auto-implement"
    )
    human_review_threshold: float = Field(
        default=0.60, ge=0.0, le=1.0, description="Minimum confidence for human review"
    )


class PRGuardianConfiguration(BaseModel):
    """Main configuration for PR Guardian agent."""

    github: GitHubSettings = Field(..., description="GitHub settings")
    repositories: list[RepositoryTarget] = Field(
        ..., min_length=1, max_length=10, description="Repositories to monitor"
    )
    feedback: FeedbackSettings = Field(
        default_factory=FeedbackSettings, description="Feedback settings"
    )
    execution: ExecutionSettings = Field(
        default_factory=ExecutionSettings, description="Execution settings"
    )
    signing: SigningConfig = Field(
        default_factory=SigningConfig, description="Signing configuration"
    )
    translation_patterns: list[str] = Field(
        default_factory=lambda: [
            "*.properties",
            "**/i18n/**/*.json",
            "**/locales/**/*.yml",
            "**/locales/**/*.yaml",
            "**/lang/**/*",
        ],
        description="Global translation file patterns",
    )
    logging: LoggingSettings = Field(
        default_factory=LoggingSettings, description="Logging settings"
    )
    llm: LLMSettings = Field(
        default_factory=LLMSettings, description="LLM settings"
    )
