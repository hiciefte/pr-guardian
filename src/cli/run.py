"""Run command for PR Guardian CLI."""

import asyncio
import signal
import sys
import logging
from pathlib import Path
from datetime import datetime, timezone

import click

from src.lib.utils import configure_logging, get_logger, format_duration
from src.models import PRGuardianConfiguration, LogLevel
from src.services import load_config
from src.services.config_loader import ConfigurationError
from src.services.session_manager import execute_session, SessionTimeoutError


logger = get_logger(__name__)


class TimeoutHandler:
    """Context manager for handling execution timeouts."""

    def __init__(self, timeout_seconds: int):
        self.timeout_seconds = timeout_seconds
        self.timed_out = False

    def __enter__(self) -> "TimeoutHandler":
        if sys.platform != "win32":
            signal.signal(signal.SIGALRM, self._handle_timeout)
            signal.alarm(self.timeout_seconds)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if sys.platform != "win32":
            signal.alarm(0)
        return False

    def _handle_timeout(self, signum: int, frame) -> None:
        self.timed_out = True
        raise SessionTimeoutError(
            f"Session timed out after {self.timeout_seconds} seconds"
        )


@click.command()
@click.option(
    "--config",
    "-c",
    "config_path",
    type=click.Path(exists=True, path_type=Path),
    default="config/config.yml",
    help="Path to configuration file.",
    show_default=True,
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would be done without making changes.",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Enable debug logging.",
)
@click.pass_context
def run(ctx: click.Context, config_path: Path, dry_run: bool, verbose: bool) -> None:
    """
    Execute PR Guardian session.

    Discovers translation PRs, processes CodeRabbitAI comments,
    and implements approved changes.
    """
    start_time = datetime.now(timezone.utc)
    exit_code = 0

    # Configure logging based on verbosity
    log_level = logging.DEBUG if verbose else logging.INFO
    configure_logging(level=log_level)

    logger.info(f"PR Guardian session starting at {start_time.isoformat()}")
    logger.info(f"Configuration file: {config_path}")

    if dry_run:
        logger.info("DRY RUN MODE: No changes will be made")

    try:
        # Load configuration
        config = load_config(config_path)

        # Override log level if verbose
        if verbose:
            config.logging.level = LogLevel.DEBUG

        # Execute session with timeout
        timeout_seconds = config.execution.timeout_seconds

        with TimeoutHandler(timeout_seconds):
            report = asyncio.run(execute_session(config, dry_run=dry_run))

        # Log session summary
        _log_session_summary(report)

        if not report.success:
            exit_code = 1
            logger.error("Session completed with failures")
        else:
            logger.info("Session completed successfully")

    except ConfigurationError as e:
        logger.exception(f"Configuration error: {e}")
        exit_code = 1
    except SessionTimeoutError as e:
        logger.exception(f"Session timeout: {e}")
        exit_code = 1
    except KeyboardInterrupt:
        logger.warning("Session interrupted by user")
        exit_code = 130
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        exit_code = 1
    finally:
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()
        logger.info(
            f"Session ended at {end_time.isoformat()} "
            f"(duration: {format_duration(duration)})"
        )

    sys.exit(exit_code)


def _log_session_summary(report) -> None:
    """Log a summary of the session report."""
    logger.info("=" * 60)
    logger.info("SESSION SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Session ID: {report.session_id}")
    logger.info(f"Duration: {format_duration(report.duration_seconds or 0)}")
    logger.info(f"Repositories: {len(report.repositories_processed)}")
    logger.info(f"PRs discovered: {report.prs_discovered}")
    logger.info(f"PRs processed: {report.prs_processed}")
    logger.info(f"PRs skipped: {report.prs_skipped}")
    logger.info(f"PRs failed: {report.prs_failed}")
    logger.info(f"Comments retrieved: {report.comments_retrieved}")
    logger.info(f"Comments classified: {report.comments_classified}")
    logger.info(f"Changes implemented: {report.changes_implemented}")
    logger.info(f"Commits created: {report.commits_created}")

    if report.feedback_issues_created > 0:
        logger.info(f"Feedback issues: {report.feedback_issues_created}")

    if report.llm_stats.requests > 0:
        logger.info(f"LLM requests: {report.llm_stats.requests}")
        logger.info(f"LLM tokens (in/out): {report.llm_stats.tokens_in}/{report.llm_stats.tokens_out}")
        logger.info(f"LLM cost estimate: ${report.llm_stats.cost_estimate:.4f}")

    if report.errors:
        logger.warning(f"Errors encountered: {len(report.errors)}")
        for error in report.errors[:5]:  # Show first 5 errors
            logger.warning(f"  - {error}")
        if len(report.errors) > 5:
            logger.warning(f"  ... and {len(report.errors) - 5} more errors")

    logger.info("=" * 60)
