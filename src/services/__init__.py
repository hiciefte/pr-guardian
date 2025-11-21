"""Business logic services for PR Guardian."""

from .comment_classifier import (
    batch_classify_comments,
    classify_comment,
)
from .comment_retrieval import (
    filter_translation_comments,
    retrieve_coderabbit_comments,
)
from .commit_builder import (
    build_batch_commit_message,
    build_commit_message,
    ensure_imperative_mood,
    validate_commit_message,
)
from .config_loader import load_config
from .git_operations import GitOperationError, GitOperations
from .github_client import GitHubAPIError, GitHubClient
from .gpg_signer import (
    GPGSigner,
    GPGSigningError,
    configure_git_signing,
)
from .llm_parser import CircuitBreaker, LLMParser, get_implementation_decision
from .pr_discovery import discover_translation_prs
from .session_manager import (
    execute_session,
    SessionError,
    SessionTimeoutError,
)
from .translation_processor import (
    apply_translation_change,
    batch_apply_changes,
    preview_change,
    validate_change_before_apply,
)
from .feedback_aggregator import (
    aggregate_feedback_patterns,
    should_create_issue,
)
from .issue_creator import IssueCreator
from .summary_poster import (
    format_summary_comment,
    post_pr_summary,
)

__all__ = [
    # Config
    "load_config",
    # GitHub
    "GitHubClient",
    "GitHubAPIError",
    # PR Discovery
    "discover_translation_prs",
    # Comment Retrieval
    "retrieve_coderabbit_comments",
    "filter_translation_comments",
    # LLM Parser
    "LLMParser",
    "CircuitBreaker",
    "get_implementation_decision",
    # Comment Classifier
    "classify_comment",
    "batch_classify_comments",
    # Translation Processor
    "apply_translation_change",
    "validate_change_before_apply",
    "preview_change",
    "batch_apply_changes",
    # Commit Builder
    "build_commit_message",
    "build_batch_commit_message",
    "validate_commit_message",
    "ensure_imperative_mood",
    # Git Operations
    "GitOperations",
    "GitOperationError",
    # GPG Signer
    "GPGSigner",
    "GPGSigningError",
    "configure_git_signing",
    # Session Manager
    "execute_session",
    "SessionError",
    "SessionTimeoutError",
    # Feedback Loop
    "aggregate_feedback_patterns",
    "should_create_issue",
    "IssueCreator",
    "format_summary_comment",
    "post_pr_summary",
]
