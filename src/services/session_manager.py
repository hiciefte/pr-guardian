"""Session manager for orchestrating PR Guardian workflow."""

import os
from datetime import datetime, timezone
from typing import Optional

import httpx

from src.lib.utils import get_logger, format_duration
from src.models import (
    PRGuardianConfiguration,
    SessionReport,
    ClassificationType,
    ImplementationDecision,
)
from .comment_classifier import pre_classify_comment
from .comment_retrieval import retrieve_coderabbit_comments
from .commit_builder import build_batch_commit_message
from .git_operations import GitOperations, GitOperationError
from .github_client import GitHubClient, GitHubAPIError
from .llm_parser import LLMParser
from .pr_discovery import discover_translation_prs
from .translation_processor import batch_apply_changes


logger = get_logger(__name__)


class SessionTimeoutError(Exception):
    """Raised when a session exceeds its timeout."""

    pass


class SessionError(Exception):
    """Raised when a session encounters a critical error."""

    pass


def execute_session(
    config: PRGuardianConfiguration,
    dry_run: bool = False,
) -> SessionReport:
    """
    Execute a complete PR Guardian session.

    Orchestrates the full workflow:
    1. Discover PRs across all repositories
    2. For each PR:
       - Retrieve CodeRabbitAI comments
       - Parse comments with LLM
       - Classify comments
       - Apply translation changes
       - Create signed commits
       - Push to PR
       - Post summary comment
    3. Create feedback issue if patterns detected
    4. Return session report

    Args:
        config: PR Guardian configuration
        dry_run: If True, show what would be done without making changes

    Returns:
        SessionReport with execution results

    Raises:
        SessionTimeoutError: If session exceeds timeout
        SessionError: If critical error occurs
    """
    report = SessionReport()

    try:
        # Initialize clients
        github_token = os.getenv(config.github.token_env)
        if not github_token:
            raise SessionError(f"GitHub token not found in {config.github.token_env}")

        github_client = GitHubClient(github_token)
        llm_parser = _initialize_llm_parser(config)

        # Ping healthchecks.io start if configured
        _ping_healthcheck(config, "start")

        # Phase 1: Discover PRs
        logger.info("Phase 1: Discovering translation PRs")

        # Track repositories
        for repo in config.repositories:
            repo_str = f"{repo.owner}/{repo.repository}"
            report.repositories_processed.append(repo_str)

        try:
            all_prs = discover_translation_prs(
                github_client,
                config.repositories,
                config.github.target_username,
            )
            logger.info(f"Discovered {len(all_prs)} PRs across {len(config.repositories)} repositories")
        except GitHubAPIError as e:
            logger.error(f"Failed to discover PRs: {e}")
            report.add_error(f"PR discovery failed: {e}")
            all_prs = []

        report.prs_discovered = len(all_prs)
        logger.info(f"Total PRs discovered: {report.prs_discovered}")

        if report.prs_discovered == 0:
            logger.info("No translation PRs found to process")
            report.complete()
            _ping_healthcheck(config, "success")
            return report

        # Phase 2: Process each PR
        logger.info("Phase 2: Processing PRs")
        for pr in all_prs:
            try:
                processed = _process_pr(
                    pr,
                    config,
                    github_client,
                    llm_parser,
                    report,
                    dry_run,
                )
                if processed:
                    report.prs_processed += 1
                else:
                    report.prs_skipped += 1
            except Exception as e:
                logger.error(f"Failed to process PR #{pr.number}: {e}")
                report.add_error(f"PR #{pr.number} processing failed: {e}")
                report.prs_failed += 1

        # Phase 3: Create feedback issues if patterns detected
        if config.feedback.repository and report.changes_implemented > 0:
            logger.info("Phase 3: Creating feedback issues")
            try:
                issues_created = _create_feedback_issues(
                    config, github_client, report, dry_run
                )
                report.feedback_issues_created = issues_created
            except Exception as e:
                logger.error(f"Failed to create feedback issues: {e}")
                report.add_error(f"Feedback issue creation failed: {e}")

        # Complete session
        report.complete()

        # Ping healthchecks.io completion
        status = "success" if report.success else "fail"
        _ping_healthcheck(config, status)

        return report

    except Exception as e:
        logger.exception(f"Session failed with critical error: {e}")
        report.add_error(f"CRITICAL: {e}")
        report.complete()
        _ping_healthcheck(config, "fail")
        return report


def _initialize_llm_parser(config: PRGuardianConfiguration) -> Optional[LLMParser]:
    """Initialize LLM parser if API key is available."""
    api_key = os.getenv(config.llm.api_key_env)
    if not api_key:
        logger.warning("LLM API key not found, LLM parsing disabled")
        return None

    return LLMParser(
        api_key=api_key,
        model=config.llm.model,
        max_tokens=config.llm.max_tokens,
        confidence_threshold=config.llm.confidence_threshold,
    )


def _process_pr(
    pr,
    config: PRGuardianConfiguration,
    github_client: GitHubClient,
    llm_parser: Optional[LLMParser],
    report: SessionReport,
    dry_run: bool,
) -> bool:
    """
    Process a single PR.

    Returns True if PR was processed, False if skipped.
    """
    logger.info(f"Processing PR #{pr.number}: {pr.title}")

    # Retrieve CodeRabbitAI comments
    comments = retrieve_coderabbit_comments(
        github_client,
        pr,
    )
    report.comments_retrieved += len(comments)

    if not comments:
        logger.info(f"No CodeRabbitAI comments found for PR #{pr.number}")
        return False

    logger.info(f"Retrieved {len(comments)} comments for PR #{pr.number}")

    # Process comments and collect changes
    changes_to_apply = []

    for comment in comments:
        # Pre-classify comment to skip non-actionable ones
        classification = pre_classify_comment(comment)
        report.increment_comments(classification.type.value)

        # Skip non-actionable comments
        if classification.type not in [
            ClassificationType.CRITICAL,
            ClassificationType.CONSTRUCTIVE,
        ]:
            continue

        # Parse with LLM if available
        if llm_parser:
            try:
                extraction = llm_parser.parse_comment(comment)

                # Update LLM stats
                report.llm_stats.requests += 1
                report.llm_stats.tokens_in += extraction.tokens_in if hasattr(extraction, 'tokens_in') else 0
                report.llm_stats.tokens_out += extraction.tokens_out if hasattr(extraction, 'tokens_out') else 0

                # Check if we should implement
                if extraction.decision == ImplementationDecision.IMPLEMENT:
                    for change in extraction.suggested_changes:
                        changes_to_apply.append((comment, change))
                elif extraction.decision == ImplementationDecision.HUMAN_REVIEW:
                    logger.info(
                        f"Comment requires human review: {comment.id} "
                        f"(confidence: {extraction.confidence})"
                    )

            except Exception as e:
                logger.error(f"LLM parsing failed for comment {comment.id}: {e}")
                report.add_error(f"LLM parsing error for comment {comment.id}: {e}")

    if not changes_to_apply:
        logger.info(f"No changes to apply for PR #{pr.number}")
        return True

    logger.info(f"Applying {len(changes_to_apply)} changes for PR #{pr.number}")

    if dry_run:
        logger.info(f"DRY RUN: Would apply {len(changes_to_apply)} changes")
        for comment, change in changes_to_apply:
            logger.info(f"  - {change.file_path}: {change.change_type.value}")
        return True

    # Apply changes
    try:
        git_ops = GitOperations(
            pr.owner,
            pr.repo_name,
            github_client.token,
        )

        # Clone repository
        work_dir = git_ops.clone_pr_branch(pr.number, pr.head_ref)

        # Apply all changes
        changes = [change for _, change in changes_to_apply]
        applied = batch_apply_changes(changes, work_dir)

        if not applied:
            logger.warning(f"No changes successfully applied for PR #{pr.number}")
            return True

        report.changes_implemented += len(applied)

        # Create commit
        commit_message = build_batch_commit_message(
            applied,
            pr.number,
            [comment for comment, _ in changes_to_apply],
        )

        # Stage and commit
        git_ops.stage_changes(applied)
        commit_hash = git_ops.commit(commit_message, config.signing)
        report.commits_created += 1

        logger.info(f"Created commit {commit_hash} for PR #{pr.number}")

        # Push changes
        git_ops.push()
        logger.info(f"Pushed changes to PR #{pr.number}")

        # Post summary comment
        summary = _build_summary_comment(applied, commit_hash)
        github_client.create_pr_comment(
            pr.owner,
            pr.repo_name,
            pr.number,
            summary,
        )

        # Cleanup
        git_ops.cleanup()

        return True

    except GitOperationError as e:
        logger.error(f"Git operation failed for PR #{pr.number}: {e}")
        report.add_error(f"Git operation failed for PR #{pr.number}: {e}")
        return True
    except Exception as e:
        logger.error(f"Failed to apply changes for PR #{pr.number}: {e}")
        report.add_error(f"Change application failed for PR #{pr.number}: {e}")
        return True


def _build_summary_comment(changes, commit_hash: str) -> str:
    """Build a summary comment for applied changes."""
    lines = [
        "## PR Guardian - Automated Changes Applied",
        "",
        f"Commit: `{commit_hash[:8]}`",
        "",
        f"**{len(changes)} translation changes applied:**",
        "",
    ]

    for change in changes:
        lines.append(f"- `{change.file_path}`: {change.change_type.value}")

    lines.extend([
        "",
        "---",
        "*This comment was generated automatically by PR Guardian.*",
    ])

    return "\n".join(lines)


def _create_feedback_issues(
    config: PRGuardianConfiguration,
    github_client: GitHubClient,
    report: SessionReport,
    dry_run: bool,
) -> int:
    """Create feedback issues for recurring patterns."""
    # Placeholder for pattern detection and feedback issue creation
    # This would analyze report.comments_by_type and create issues
    # for recurring patterns that need attention

    if dry_run:
        logger.info("DRY RUN: Would create feedback issues based on patterns")
        return 0

    # TODO: Implement pattern detection and feedback issue creation
    return 0


def _ping_healthcheck(
    config: PRGuardianConfiguration,
    status: str,
) -> None:
    """
    Ping healthchecks.io endpoint.

    Args:
        config: Configuration containing healthcheck settings
        status: One of "start", "success", "fail"
    """
    healthcheck_url = os.getenv("HEALTHCHECKS_URL")
    if not healthcheck_url:
        return

    try:
        url = healthcheck_url
        if status == "start":
            url = f"{healthcheck_url}/start"
        elif status == "fail":
            url = f"{healthcheck_url}/fail"

        with httpx.Client(timeout=10.0) as client:
            client.get(url)
        logger.debug(f"Healthcheck ping sent: {status}")
    except Exception as e:
        logger.warning(f"Failed to ping healthcheck: {e}")
