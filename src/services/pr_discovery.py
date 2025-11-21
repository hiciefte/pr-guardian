"""PR Discovery Service for finding translation PRs."""

import fnmatch
import logging
from datetime import datetime

from src.models import PRState, RepositoryTarget, TranslationPullRequest
from src.services.github_client import GitHubClient

logger = logging.getLogger(__name__)


def discover_translation_prs(
    client: GitHubClient,
    repos: list[RepositoryTarget],
    author: str,
) -> list[TranslationPullRequest]:
    """
    Discover translation PRs across multiple repositories.

    Filters PRs by author, state (open), and branch filter if configured.
    Identifies which files are translation files based on repository patterns.

    Args:
        client: GitHub client for API calls
        repos: List of repository targets to search
        author: PR author username to filter by

    Returns:
        List of discovered translation PRs

    Example:
        client = GitHubClient()
        repos = [RepositoryTarget(owner="org", repository="app")]
        prs = discover_translation_prs(client, repos, "translator-bot")
    """
    discovered_prs: list[TranslationPullRequest] = []

    for repo in repos:
        if not repo.enabled:
            logger.debug(f"Skipping disabled repository: {repo.full_name}")
            continue

        logger.info(f"Discovering PRs in {repo.full_name} by {author}")

        try:
            pr_list = client.list_prs(
                owner=repo.owner,
                repo=repo.repository,
                author=author,
                state="open",
            )
        except Exception as e:
            logger.error(f"Failed to list PRs in {repo.full_name}: {e}")
            continue

        for pr_data in pr_list:
            # Apply branch filter if configured
            if repo.branch_filter:
                target_branch = pr_data.get("baseRefName", "")
                if target_branch != repo.branch_filter:
                    logger.debug(
                        f"PR #{pr_data['number']} targets {target_branch}, "
                        f"skipping (filter: {repo.branch_filter})"
                    )
                    continue

            # Get files changed in PR
            try:
                files = client.get_pr_files(
                    owner=repo.owner,
                    repo=repo.repository,
                    pr_number=pr_data["number"],
                )
            except Exception as e:
                logger.warning(
                    f"Failed to get files for PR #{pr_data['number']}: {e}"
                )
                files = []

            # Identify translation files
            translation_files = _identify_translation_files(
                files,
                repo.translation_file_patterns,
            )

            if not translation_files:
                logger.debug(
                    f"PR #{pr_data['number']} has no translation files, skipping"
                )
                continue

            # Get comment count
            try:
                comments = client.get_pr_comments(
                    owner=repo.owner,
                    repo=repo.repository,
                    pr_number=pr_data["number"],
                )
                comment_count = len(comments)
            except Exception:
                comment_count = 0

            # Convert to TranslationPullRequest model
            pr = _convert_to_model(
                pr_data=pr_data,
                owner=repo.owner,
                repo=repo.repository,
                author=author,
                translation_files=translation_files,
                comment_count=comment_count,
            )
            discovered_prs.append(pr)
            logger.info(
                f"Discovered PR #{pr.number}: {pr.title} "
                f"({len(translation_files)} translation files)"
            )

    logger.info(f"Discovered {len(discovered_prs)} translation PRs total")
    return discovered_prs


def _identify_translation_files(
    files: list[dict],
    patterns: list[str],
) -> list[str]:
    """
    Identify which files are translation files based on patterns.

    Args:
        files: List of file objects from GitHub API
        patterns: Glob patterns to match translation files

    Returns:
        List of file paths that match translation patterns
    """
    translation_files: list[str] = []

    for file_obj in files:
        file_path = file_obj.get("path", file_obj.get("filename", ""))
        if not file_path:
            continue

        for pattern in patterns:
            if _matches_pattern(file_path, pattern):
                translation_files.append(file_path)
                break

    return translation_files


def _matches_pattern(file_path: str, pattern: str) -> bool:
    """
    Check if file path matches a glob pattern.

    Supports:
    - Simple wildcards: *.properties
    - Directory wildcards: **/locales/**
    - Combined patterns: **/i18n/**/*.json

    Args:
        file_path: File path to check
        pattern: Glob pattern to match

    Returns:
        True if file matches pattern
    """
    # Normalize path separators
    file_path = file_path.replace("\\", "/")
    pattern = pattern.replace("\\", "/")

    # Handle ** (recursive) patterns
    if "**" in pattern:
        # Split pattern into parts
        parts = pattern.split("**")
        if len(parts) == 2:
            prefix, suffix = parts
            prefix = prefix.rstrip("/")
            suffix = suffix.lstrip("/")

            # Check prefix
            if prefix and not file_path.startswith(prefix):
                return False

            # Check suffix
            if suffix:
                remaining = file_path[len(prefix):].lstrip("/")
                # Use fnmatch for the suffix part
                return any(
                    fnmatch.fnmatch(remaining, f"*{suffix}")
                    or fnmatch.fnmatch(remaining, f"*/{suffix}")
                    for _ in [None]
                ) or fnmatch.fnmatch(remaining, suffix)

            return True

    # Simple fnmatch for non-recursive patterns
    return fnmatch.fnmatch(file_path, pattern)


def _convert_to_model(
    pr_data: dict,
    owner: str,
    repo: str,
    author: str,
    translation_files: list[str],
    comment_count: int,
) -> TranslationPullRequest:
    """
    Convert GitHub API PR data to TranslationPullRequest model.

    Args:
        pr_data: Raw PR data from GitHub API
        owner: Repository owner
        repo: Repository name
        author: PR author username
        translation_files: List of translation file paths
        comment_count: Number of comments on PR

    Returns:
        TranslationPullRequest model instance
    """
    # Parse dates
    created_at = datetime.fromisoformat(
        pr_data["createdAt"].replace("Z", "+00:00")
    )
    updated_at = datetime.fromisoformat(
        pr_data["updatedAt"].replace("Z", "+00:00")
    )

    # Map state
    state_map = {
        "OPEN": PRState.OPEN,
        "CLOSED": PRState.CLOSED,
        "MERGED": PRState.MERGED,
    }
    state = state_map.get(pr_data.get("state", "").upper(), PRState.OPEN)

    return TranslationPullRequest(
        owner=owner,
        repo_name=repo,
        number=pr_data["number"],
        title=pr_data["title"],
        url=pr_data.get("url", f"https://github.com/{owner}/{repo}/pull/{pr_data['number']}"),
        state=state,
        source_branch=pr_data.get("headRefName", "unknown"),
        target_branch=pr_data.get("baseRefName", "main"),
        created_at=created_at,
        updated_at=updated_at,
        author=author,
        translation_files=translation_files,
        comment_count=comment_count,
    )
