"""GitHub CLI wrapper for PR Guardian."""

import json
import logging
import os
import re
import subprocess
from typing import Any, Optional

from src.lib.utils.retry import RateLimitError, ServerError, retry_with_backoff

logger = logging.getLogger(__name__)


class GitHubAPIError(Exception):
    """
    Raised when GitHub CLI command fails.

    Attributes:
        error_type: Type of error (rate_limit, not_found, authentication, etc.)
        retryable: Whether the error is retryable
        message: Error message
    """

    def __init__(self, message: str, error_type: str = "unknown", retryable: bool = False):
        super().__init__(message)
        self.error_type = error_type
        self.retryable = retryable


class GitHubClient:
    """
    GitHub CLI wrapper for PR Guardian operations.

    Uses subprocess to call `gh` CLI commands with JSON output format.
    Includes multi-level error detection and automatic retry with backoff.
    """

    def __init__(self, token: Optional[str] = None, token_env: str = "GITHUB_TOKEN"):
        """
        Initialize GitHub client.

        Args:
            token: GitHub token (optional, uses env var if not provided)
            token_env: Environment variable name for GitHub token
        """
        self._token = token or os.getenv(token_env)
        self._token_env = token_env

        if not self._token:
            raise GitHubAPIError(
                f"GitHub token not found. Set {token_env} environment variable.",
                error_type="authentication",
                retryable=False,
            )

    def _run_gh_command(
        self, args: list[str], check: bool = True
    ) -> subprocess.CompletedProcess:
        """
        Execute a gh CLI command.

        Args:
            args: Command arguments (without 'gh' prefix)
            check: Whether to raise on non-zero exit code

        Returns:
            CompletedProcess with stdout/stderr

        Raises:
            GitHubAPIError: On command failure
        """
        cmd = ["gh"] + args
        logger.debug(f"Running gh command: {' '.join(cmd)}")

        env = os.environ.copy()
        env["GH_TOKEN"] = self._token

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env,
                timeout=60,
            )
        except subprocess.TimeoutExpired:
            raise GitHubAPIError(
                "GitHub CLI command timed out",
                error_type="timeout",
                retryable=True,
            )

        if result.returncode != 0:
            error_info = self._parse_gh_error(result.returncode, result.stderr)
            error = GitHubAPIError(
                f"GitHub CLI error: {result.stderr.strip() or 'Unknown error'}",
                error_type=error_info["type"],
                retryable=error_info["retryable"],
            )

            # Raise specific exception types for retry decorator
            if error_info["retryable"]:
                if error_info["type"] == "rate_limit":
                    raise RateLimitError(str(error))
                elif error_info["type"] == "server_error":
                    raise ServerError(str(error))

            raise error

        return result

    def _parse_gh_error(self, exit_code: int, stderr: str) -> dict[str, Any]:
        """
        Multi-level error detection for gh CLI.

        Args:
            exit_code: Process exit code
            stderr: Standard error output

        Returns:
            Dict with 'type' and 'retryable' keys
        """
        # Level 1: Exit code analysis
        exit_code_types = {
            1: "general_error",
            2: "usage_error",
            3: "authentication_error",
            4: "not_found_error",
        }

        # Level 2: HTTP status extraction from stderr
        http_match = re.search(r"HTTP (\d{3})", stderr)
        if http_match:
            status_code = int(http_match.group(1))
            if status_code == 401:
                return {"type": "authentication", "retryable": False}
            if status_code == 403:
                return {"type": "rate_limit", "retryable": True}
            if status_code == 404:
                return {"type": "not_found", "retryable": False}
            if status_code == 422:
                return {"type": "validation_error", "retryable": False}
            if status_code >= 500:
                return {"type": "server_error", "retryable": True}

        # Level 3: Stderr message parsing
        stderr_lower = stderr.lower()
        if "not found" in stderr_lower:
            return {"type": "not_found", "retryable": False}
        if "rate limit" in stderr_lower:
            return {"type": "rate_limit", "retryable": True}
        if "permission" in stderr_lower or "forbidden" in stderr_lower:
            return {"type": "permission", "retryable": False}
        if "authentication" in stderr_lower or "credentials" in stderr_lower:
            return {"type": "authentication", "retryable": False}
        if "timeout" in stderr_lower:
            return {"type": "timeout", "retryable": True}
        if "connection" in stderr_lower:
            return {"type": "connection", "retryable": True}

        return {
            "type": exit_code_types.get(exit_code, "unknown"),
            "retryable": False,
        }

    @retry_with_backoff(max_attempts=3)
    def auth_status(self) -> dict[str, Any]:
        """
        Verify GitHub CLI authentication status.

        Returns:
            Dict with authentication status information

        Raises:
            GitHubAPIError: On authentication failure
        """
        result = self._run_gh_command(["auth", "status"])

        # Parse output to extract status info
        output = result.stdout + result.stderr

        return {
            "authenticated": "Logged in" in output,
        }

    @retry_with_backoff(max_attempts=5)
    def list_prs(
        self,
        owner: str,
        repo: str,
        author: str,
        state: str = "open",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        List pull requests from a repository.

        Args:
            owner: Repository owner
            repo: Repository name
            author: PR author username
            state: PR state (open, closed, merged, all)
            limit: Maximum number of PRs to return

        Returns:
            List of PR objects with number, title, state, url, etc.

        Raises:
            GitHubAPIError: On API failure
        """
        result = self._run_gh_command([
            "pr", "list",
            "--repo", f"{owner}/{repo}",
            "--author", author,
            "--state", state,
            "--limit", str(limit),
            "--json", "number,title,state,url,headRefName,baseRefName,createdAt,updatedAt",
        ])

        if not result.stdout.strip():
            return []

        return json.loads(result.stdout)

    @retry_with_backoff(max_attempts=5)
    def get_pr(self, owner: str, repo: str, pr_number: int) -> dict[str, Any]:
        """
        Get detailed information about a pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number

        Returns:
            PR object with full details

        Raises:
            GitHubAPIError: On API failure
        """
        result = self._run_gh_command([
            "pr", "view",
            str(pr_number),
            "--repo", f"{owner}/{repo}",
            "--json", "number,title,state,url,body,headRefName,baseRefName,"
                      "createdAt,updatedAt,author,reviewDecision,isDraft,"
                      "additions,deletions,changedFiles",
        ])

        return json.loads(result.stdout)

    @retry_with_backoff(max_attempts=5)
    def get_pr_comments(
        self, owner: str, repo: str, pr_number: int
    ) -> list[dict[str, Any]]:
        """
        Get review comments on a pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number

        Returns:
            List of review comment objects

        Raises:
            GitHubAPIError: On API failure
        """
        # Get PR review comments using API
        result = self._run_gh_command([
            "api",
            f"repos/{owner}/{repo}/pulls/{pr_number}/comments",
            "--paginate",
        ])

        if not result.stdout.strip():
            return []

        return json.loads(result.stdout)

    @retry_with_backoff(max_attempts=5)
    def get_pr_files(
        self, owner: str, repo: str, pr_number: int
    ) -> list[dict[str, Any]]:
        """
        Get list of files changed in a pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number

        Returns:
            List of file objects with filename, status, additions, deletions

        Raises:
            GitHubAPIError: On API failure
        """
        result = self._run_gh_command([
            "pr", "view",
            str(pr_number),
            "--repo", f"{owner}/{repo}",
            "--json", "files",
        ])

        data = json.loads(result.stdout)
        return data.get("files", [])

    @retry_with_backoff(max_attempts=3)
    def create_comment(
        self, owner: str, repo: str, pr_number: int, body: str
    ) -> dict[str, Any]:
        """
        Create a comment on a pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number
            body: Comment body text

        Returns:
            Created comment object

        Raises:
            GitHubAPIError: On API failure
        """
        result = self._run_gh_command([
            "pr", "comment",
            str(pr_number),
            "--repo", f"{owner}/{repo}",
            "--body", body,
        ])

        # gh pr comment doesn't return JSON, return success indicator
        return {
            "success": True,
            "pr_number": pr_number,
            "body_length": len(body),
        }

    @retry_with_backoff(max_attempts=3)
    def create_issue(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str,
        labels: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """
        Create an issue in a repository.

        Args:
            owner: Repository owner
            repo: Repository name
            title: Issue title
            body: Issue body text
            labels: List of labels to apply

        Returns:
            Created issue object with number and url

        Raises:
            GitHubAPIError: On API failure
        """
        cmd = [
            "issue", "create",
            "--repo", f"{owner}/{repo}",
            "--title", title,
            "--body", body,
        ]

        if labels:
            for label in labels:
                cmd.extend(["--label", label])

        result = self._run_gh_command(cmd)

        # Parse issue URL from output
        issue_url = result.stdout.strip()
        issue_number = int(issue_url.split("/")[-1]) if issue_url else 0

        return {
            "number": issue_number,
            "url": issue_url,
            "title": title,
        }

    @retry_with_backoff(max_attempts=3)
    def get_rate_limit(self) -> dict[str, Any]:
        """
        Get current API rate limit status.

        Returns:
            Rate limit information

        Raises:
            GitHubAPIError: On API failure
        """
        result = self._run_gh_command([
            "api", "rate_limit",
        ])

        return json.loads(result.stdout)
