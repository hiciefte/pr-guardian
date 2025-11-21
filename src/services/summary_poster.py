"""PR summary comment posting service for PR Guardian."""

import logging
from typing import Any

from src.models import (
    ClassificationType,
    CommentClassification,
    TranslationPullRequest,
)
from src.services.github_client import GitHubClient

logger = logging.getLogger(__name__)


def post_pr_summary(
    client: GitHubClient,
    pr: TranslationPullRequest,
    classifications: list[CommentClassification],
    commit_results: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Post a summary comment to a PR after processing.

    Creates a markdown summary with implementation statistics,
    breakdown by classification type, commits created, and items
    flagged for review.

    Args:
        client: GitHubClient instance for API operations
        pr: TranslationPullRequest being processed
        classifications: List of comment classifications
        commit_results: List of commit result dictionaries

    Returns:
        Result dictionary from comment creation

    Raises:
        GitHubAPIError: On comment posting failure
    """
    # Use owner and repo_name from PR model
    owner = pr.owner
    repo = pr.repo_name

    # Generate summary comment
    comment_body = format_summary_comment(classifications, commit_results)

    # Post comment
    result = client.create_comment(
        owner=owner,
        repo=repo,
        pr_number=pr.number,
        body=comment_body,
    )

    logger.info(f"Posted summary comment to PR #{pr.number} in {owner}/{repo}")

    return result


def format_summary_comment(
    classifications: list[CommentClassification],
    commit_results: list[dict[str, Any]],
) -> str:
    """
    Generate markdown summary comment.

    Args:
        classifications: List of comment classifications
        commit_results: List of commit result dictionaries

    Returns:
        Formatted markdown string
    """
    sections = [
        _format_header(),
        _format_statistics_table(classifications, commit_results),
        _format_classification_breakdown(classifications),
        _format_commits_section(commit_results),
        _format_human_review_section(classifications),
        _format_skipped_section(classifications),
        _format_footer(),
    ]

    return "\n\n".join(filter(None, sections))


def _format_header() -> str:
    """Format comment header."""
    return (
        "## PR Guardian Summary\n\n"
        "Automated processing of CodeRabbitAI review comments completed."
    )


def _format_statistics_table(
    classifications: list[CommentClassification],
    commit_results: list[dict[str, Any]],
) -> str:
    """Format implementation statistics table."""
    total = len(classifications)
    implemented = sum(1 for c in classifications if c.should_implement)
    skipped = total - implemented
    commits = len(commit_results)
    human_review = sum(1 for c in classifications if c.requires_human_review)

    # Calculate success rate
    success_rate = (implemented / total * 100) if total > 0 else 0

    return (
        "### Implementation Statistics\n\n"
        "| Metric | Count |\n"
        "|--------|-------|\n"
        f"| Total Comments Processed | {total} |\n"
        f"| Changes Implemented | {implemented} |\n"
        f"| Items Skipped | {skipped} |\n"
        f"| Commits Created | {commits} |\n"
        f"| Flagged for Human Review | {human_review} |\n"
        f"| Success Rate | {success_rate:.1f}% |"
    )


def _format_classification_breakdown(
    classifications: list[CommentClassification],
) -> str:
    """Format breakdown by classification type."""
    # Count by type
    type_counts: dict[str, dict[str, int]] = {}

    for c in classifications:
        type_name = c.type.value
        if type_name not in type_counts:
            type_counts[type_name] = {"total": 0, "implemented": 0}

        type_counts[type_name]["total"] += 1
        if c.should_implement:
            type_counts[type_name]["implemented"] += 1

    # Define display order
    type_order = [
        ClassificationType.CRITICAL.value,
        ClassificationType.CONSTRUCTIVE.value,
        ClassificationType.NITPICK.value,
        ClassificationType.QUESTION.value,
        ClassificationType.PRAISE.value,
    ]

    lines = [
        "### Classification Breakdown\n",
        "| Type | Total | Implemented | Rate |",
        "|------|-------|-------------|------|",
    ]

    for type_name in type_order:
        if type_name in type_counts:
            counts = type_counts[type_name]
            rate = (
                counts["implemented"] / counts["total"] * 100
                if counts["total"] > 0
                else 0
            )
            icon = _get_type_icon(type_name)
            lines.append(
                f"| {icon} {type_name} | {counts['total']} | "
                f"{counts['implemented']} | {rate:.0f}% |"
            )

    return "\n".join(lines)


def _format_commits_section(commit_results: list[dict[str, Any]]) -> str:
    """Format commits created section."""
    if not commit_results:
        return ""

    lines = ["### Commits Created\n"]

    for i, commit in enumerate(commit_results, 1):
        sha = commit.get("sha", "unknown")[:7]
        message = commit.get("message", "No message")
        # Truncate long messages
        if len(message) > 80:
            message = message[:77] + "..."

        lines.append(f"{i}. `{sha}` - {message}")

    return "\n".join(lines)


def _format_human_review_section(
    classifications: list[CommentClassification],
) -> str:
    """Format items flagged for human review."""
    review_items = [c for c in classifications if c.requires_human_review]

    if not review_items:
        return ""

    lines = [
        "### Items Requiring Human Review\n",
        "The following items need manual attention:\n",
    ]

    for item in review_items:
        reason = (
            "Glossary conflict"
            if item.glossary_conflict
            else item.skip_reason or "Review needed"
        )
        confidence = f"{item.confidence * 100:.0f}%"
        lines.append(
            f"- **Comment #{item.comment_id}** ({item.type.value}): "
            f"{reason} (confidence: {confidence})"
        )

    return "\n".join(lines)


def _format_skipped_section(
    classifications: list[CommentClassification],
) -> str:
    """Format skipped items with reasons."""
    skipped = [c for c in classifications if not c.should_implement]

    if not skipped:
        return ""

    lines = [
        "### Skipped Items\n",
        "<details>\n<summary>Click to expand skipped items</summary>\n",
    ]

    # Group by skip reason
    by_reason: dict[str, list[int]] = {}
    for item in skipped:
        reason = item.skip_reason or "No reason provided"
        if reason not in by_reason:
            by_reason[reason] = []
        by_reason[reason].append(item.comment_id)

    for reason, comment_ids in by_reason.items():
        ids_str = ", ".join(f"#{cid}" for cid in comment_ids)
        lines.append(f"- **{reason}**: {ids_str}")

    lines.append("\n</details>")

    return "\n".join(lines)


def _format_footer() -> str:
    """Format comment footer."""
    return (
        "---\n"
        "*Automated by [PR Guardian](https://github.com/pr-guardian/pr-guardian)*"
    )


def _get_type_icon(type_name: str) -> str:
    """Get icon for classification type."""
    icons = {
        "Critical": "!!",
        "Constructive": "+",
        "Nitpick": "~",
        "Question": "?",
        "Praise": "*",
    }
    return icons.get(type_name, "-")
