"""Comment Retrieval Service for fetching CodeRabbitAI comments."""

import logging
import re
from datetime import datetime

from src.models import ReviewComment, TranslationPullRequest
from src.services.github_client import GitHubClient

logger = logging.getLogger(__name__)

# CodeRabbitAI author identifiers
CODERABBIT_AUTHORS = ["coderabbitai[bot]", "coderabbitai"]

# CodeRabbitAI markers in comment body
CODERABBIT_MARKERS = [
    "<!-- coderabbit",
    "CodeRabbitAI",
    "coderabbit.ai",
    "[CodeRabbit]",
]

# Conventional comment labels from CodeRabbitAI
CONVENTIONAL_LABELS = [
    "nitpick",
    "suggestion",
    "issue",
    "critical",
    "question",
    "praise",
    "typo",
    "style",
]


def retrieve_coderabbit_comments(
    client: GitHubClient,
    pr: TranslationPullRequest,
) -> list[ReviewComment]:
    """
    Retrieve CodeRabbitAI review comments from a PR.

    Filters comments by author "coderabbitai[bot]" or containing
    CodeRabbitAI markers. Extracts conventional labels and diff hunks.

    Args:
        client: GitHub client for API calls
        pr: Translation pull request to get comments from

    Returns:
        List of CodeRabbitAI review comments

    Example:
        client = GitHubClient()
        pr = TranslationPullRequest(...)
        comments = retrieve_coderabbit_comments(client, pr)
    """
    # Extract owner/repo from PR URL
    owner, repo = _extract_repo_info(pr.url)

    logger.info(f"Retrieving comments from PR #{pr.number}")

    try:
        raw_comments = client.get_pr_comments(
            owner=owner,
            repo=repo,
            pr_number=pr.number,
        )
    except Exception as e:
        logger.error(f"Failed to retrieve comments: {e}")
        return []

    coderabbit_comments: list[ReviewComment] = []

    for comment_data in raw_comments:
        # Check if comment is from CodeRabbitAI
        if not _is_coderabbit_comment(comment_data):
            continue

        # Convert to ReviewComment model
        review_comment = _convert_to_model(comment_data)
        if review_comment:
            coderabbit_comments.append(review_comment)

    logger.info(
        f"Found {len(coderabbit_comments)} CodeRabbitAI comments "
        f"in PR #{pr.number}"
    )

    return coderabbit_comments


def _extract_repo_info(url: str) -> tuple[str, str]:
    """
    Extract owner and repository from GitHub PR URL.

    Args:
        url: GitHub PR URL

    Returns:
        Tuple of (owner, repository)

    Raises:
        ValueError: If URL format is invalid
    """
    # https://github.com/owner/repo/pull/123
    match = re.match(r"https://github\.com/([^/]+)/([^/]+)/pull/\d+", url)
    if not match:
        raise ValueError(f"Invalid GitHub PR URL: {url}")
    return match.group(1), match.group(2)


def _is_coderabbit_comment(comment_data: dict) -> bool:
    """
    Check if a comment is from CodeRabbitAI.

    Args:
        comment_data: Raw comment data from GitHub API

    Returns:
        True if comment is from CodeRabbitAI
    """
    # Check author
    user = comment_data.get("user", {})
    author = user.get("login", "").lower()

    if any(coderabbit.lower() in author for coderabbit in CODERABBIT_AUTHORS):
        return True

    # Check for markers in body
    body = comment_data.get("body", "")
    for marker in CODERABBIT_MARKERS:
        if marker.lower() in body.lower():
            return True

    return False


def _extract_conventional_label(body: str) -> str | None:
    """
    Extract conventional label from comment body.

    CodeRabbitAI uses labels like [nitpick], **suggestion:**, etc.

    Args:
        body: Comment body text

    Returns:
        Extracted label or None
    """
    # Pattern: [label] at start or **label:** anywhere
    patterns = [
        r"^\s*\[(\w+)\]",           # [nitpick]
        r"\*\*(\w+):\*\*",          # **suggestion:**
        r"^(\w+):",                  # nitpick:
        r"<!-- type: (\w+) -->",     # <!-- type: nitpick -->
    ]

    for pattern in patterns:
        match = re.search(pattern, body, re.MULTILINE | re.IGNORECASE)
        if match:
            label = match.group(1).lower()
            if label in CONVENTIONAL_LABELS:
                return label

    return None


def _convert_to_model(comment_data: dict) -> ReviewComment | None:
    """
    Convert GitHub API comment data to ReviewComment model.

    Args:
        comment_data: Raw comment data from GitHub API

    Returns:
        ReviewComment model instance or None if conversion fails
    """
    try:
        # Parse created_at
        created_str = comment_data.get("created_at", "")
        if created_str:
            created_at = datetime.fromisoformat(
                created_str.replace("Z", "+00:00")
            )
        else:
            created_at = datetime.utcnow()

        # Get author
        user = comment_data.get("user", {})
        author = user.get("login", "unknown")

        # Get body
        body = comment_data.get("body", "")
        if not body:
            logger.debug(f"Skipping comment {comment_data.get('id')} - empty body")
            return None

        # Extract conventional label
        conventional_label = _extract_conventional_label(body)

        # Get file path and line info
        file_path = comment_data.get("path")
        line_number = (
            comment_data.get("line")
            or comment_data.get("original_line")
            or comment_data.get("position")
        )
        diff_hunk = comment_data.get("diff_hunk")

        # Build comment URL
        html_url = comment_data.get("html_url", "")
        if not html_url:
            html_url = comment_data.get("url", "").replace(
                "api.github.com/repos",
                "github.com"
            )

        return ReviewComment(
            id=comment_data["id"],
            body=body,
            author=author,
            created_at=created_at,
            url=html_url,
            file_path=file_path,
            line_number=line_number,
            diff_hunk=diff_hunk,
            conventional_label=conventional_label,
        )

    except Exception as e:
        logger.warning(
            f"Failed to convert comment {comment_data.get('id')}: {e}"
        )
        return None


def filter_translation_comments(
    comments: list[ReviewComment],
    translation_files: list[str],
) -> list[ReviewComment]:
    """
    Filter comments to only those related to translation files.

    Args:
        comments: List of review comments
        translation_files: List of translation file paths in the PR

    Returns:
        Comments that are related to translation files
    """
    if not translation_files:
        return comments

    filtered: list[ReviewComment] = []

    for comment in comments:
        # Include comments without file_path (general comments)
        if not comment.file_path:
            # Check if body mentions any translation file
            mentions_translation = any(
                tf in comment.body for tf in translation_files
            )
            if mentions_translation:
                filtered.append(comment)
            continue

        # Include if file_path is a translation file
        if comment.file_path in translation_files:
            filtered.append(comment)

    return filtered
