"""Git Operations Service for repository management."""

import logging
import os
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class GitOperationError(Exception):
    """Raised when a git operation fails."""

    def __init__(self, message: str, command: str | None = None, returncode: int | None = None):
        super().__init__(message)
        self.command = command
        self.returncode = returncode


class GitOperations:
    """
    Git operations service for repository management.

    Provides methods for common git operations using subprocess.
    """

    def __init__(
        self,
        repo_path: Path | None = None,
        git_binary: str = "git",
    ):
        """
        Initialize git operations service.

        Args:
            repo_path: Path to repository (defaults to current directory)
            git_binary: Path to git binary
        """
        self.repo_path = repo_path or Path.cwd()
        self.git_binary = git_binary

    def _run_git(
        self,
        args: list[str],
        check: bool = True,
        capture_output: bool = True,
    ) -> subprocess.CompletedProcess:
        """
        Run a git command.

        Args:
            args: Command arguments (without 'git' prefix)
            check: Whether to raise on non-zero exit code
            capture_output: Whether to capture stdout/stderr

        Returns:
            CompletedProcess with stdout/stderr

        Raises:
            GitOperationError: On command failure
        """
        cmd = [self.git_binary] + args
        logger.debug(f"Running: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=capture_output,
                text=True,
                timeout=120,
            )

            if check and result.returncode != 0:
                raise GitOperationError(
                    f"Git command failed: {result.stderr.strip() or result.stdout.strip()}",
                    command=" ".join(cmd),
                    returncode=result.returncode,
                )

            return result

        except subprocess.TimeoutExpired as e:
            raise GitOperationError(
                f"Git command timed out: {' '.join(cmd)}",
                command=" ".join(cmd),
            ) from e

    def clone_repository(
        self,
        url: str,
        path: Path,
        branch: str | None = None,
        depth: int | None = 1,
    ) -> None:
        """
        Clone a repository.

        Args:
            url: Repository URL
            path: Destination path
            branch: Branch to clone (optional)
            depth: Clone depth for shallow clone (optional)

        Raises:
            GitOperationError: On clone failure
        """
        args = ["clone"]

        if branch:
            args.extend(["--branch", branch])

        if depth:
            args.extend(["--depth", str(depth)])

        args.extend([url, str(path)])

        # Clone runs from parent directory
        result = subprocess.run(
            [self.git_binary] + args,
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode != 0:
            raise GitOperationError(
                f"Clone failed: {result.stderr.strip()}",
                command=f"git {' '.join(args)}",
                returncode=result.returncode,
            )

        logger.info(f"Cloned {url} to {path}")

    def checkout_branch(
        self,
        branch: str,
        create: bool = False,
    ) -> None:
        """
        Checkout a branch.

        Args:
            branch: Branch name
            create: Whether to create the branch if it doesn't exist

        Raises:
            GitOperationError: On checkout failure
        """
        args = ["checkout"]

        if create:
            args.append("-b")

        args.append(branch)

        self._run_git(args)
        logger.info(f"Checked out branch: {branch}")

    def stage_file(self, file_path: str) -> None:
        """
        Stage a file for commit.

        Args:
            file_path: Path to file (relative to repo root)

        Raises:
            GitOperationError: On staging failure
        """
        self._run_git(["add", file_path])
        logger.debug(f"Staged: {file_path}")

    def stage_all(self) -> None:
        """
        Stage all changes.

        Raises:
            GitOperationError: On staging failure
        """
        self._run_git(["add", "-A"])
        logger.debug("Staged all changes")

    def create_commit(
        self,
        message: str,
        sign: bool = False,
    ) -> str:
        """
        Create a commit.

        Args:
            message: Commit message
            sign: Whether to sign the commit with GPG

        Returns:
            Commit SHA

        Raises:
            GitOperationError: On commit failure
        """
        args = ["commit", "-m", message]

        if sign:
            args.append("-S")

        self._run_git(args)

        # Get commit SHA
        result = self._run_git(["rev-parse", "HEAD"])
        sha = result.stdout.strip()

        logger.info(f"Created commit: {sha[:8]}")
        return sha

    def create_signed_commit(
        self,
        message: str,
        sign: bool = True,
    ) -> str:
        """
        Create a signed commit.

        Args:
            message: Commit message
            sign: Whether to sign (default True)

        Returns:
            Commit SHA

        Raises:
            GitOperationError: On commit failure
        """
        return self.create_commit(message, sign=sign)

    def push_commits(
        self,
        branch: str,
        remote: str = "origin",
        force: bool = False,
        set_upstream: bool = False,
    ) -> None:
        """
        Push commits to remote.

        Args:
            branch: Branch to push
            remote: Remote name
            force: Whether to force push
            set_upstream: Whether to set upstream tracking

        Raises:
            GitOperationError: On push failure
        """
        args = ["push", remote, branch]

        if force:
            args.append("--force")

        if set_upstream:
            args.append("--set-upstream")

        self._run_git(args)
        logger.info(f"Pushed to {remote}/{branch}")

    def rollback_to_commit(self, sha: str) -> None:
        """
        Rollback to a specific commit.

        Uses soft reset to preserve working directory.

        Args:
            sha: Commit SHA to rollback to

        Raises:
            GitOperationError: On rollback failure
        """
        self._run_git(["reset", "--soft", sha])
        logger.info(f"Rolled back to: {sha[:8]}")

    def hard_reset(self, sha: str) -> None:
        """
        Hard reset to a specific commit.

        WARNING: This discards all changes.

        Args:
            sha: Commit SHA to reset to

        Raises:
            GitOperationError: On reset failure
        """
        self._run_git(["reset", "--hard", sha])
        logger.warning(f"Hard reset to: {sha[:8]}")

    def get_current_branch(self) -> str:
        """
        Get current branch name.

        Returns:
            Current branch name

        Raises:
            GitOperationError: On failure
        """
        result = self._run_git(["rev-parse", "--abbrev-ref", "HEAD"])
        return result.stdout.strip()

    def get_current_sha(self) -> str:
        """
        Get current commit SHA.

        Returns:
            Current commit SHA

        Raises:
            GitOperationError: On failure
        """
        result = self._run_git(["rev-parse", "HEAD"])
        return result.stdout.strip()

    def get_status(self) -> dict:
        """
        Get repository status.

        Returns:
            Status dict with staged, unstaged, and untracked files

        Raises:
            GitOperationError: On failure
        """
        result = self._run_git(["status", "--porcelain"])
        lines = result.stdout.strip().split("\n") if result.stdout.strip() else []

        staged: list[str] = []
        unstaged: list[str] = []
        untracked: list[str] = []

        for line in lines:
            if not line:
                continue

            status = line[:2]
            file_path = line[3:]

            if status[0] in "MADRC":
                staged.append(file_path)

            if status[1] in "MADRC":
                unstaged.append(file_path)

            if status == "??":
                untracked.append(file_path)

        return {
            "staged": staged,
            "unstaged": unstaged,
            "untracked": untracked,
        }

    def has_changes(self) -> bool:
        """
        Check if there are uncommitted changes.

        Returns:
            True if there are changes
        """
        status = self.get_status()
        return bool(status["staged"] or status["unstaged"])

    def fetch(self, remote: str = "origin") -> None:
        """
        Fetch from remote.

        Args:
            remote: Remote name

        Raises:
            GitOperationError: On failure
        """
        self._run_git(["fetch", remote])
        logger.debug(f"Fetched from {remote}")

    def pull(
        self,
        remote: str = "origin",
        branch: str | None = None,
        rebase: bool = False,
    ) -> None:
        """
        Pull from remote.

        Args:
            remote: Remote name
            branch: Branch to pull (defaults to current)
            rebase: Whether to rebase instead of merge

        Raises:
            GitOperationError: On failure
        """
        args = ["pull", remote]

        if branch:
            args.append(branch)

        if rebase:
            args.append("--rebase")

        self._run_git(args)
        logger.info(f"Pulled from {remote}")

    def stash(self, message: str | None = None) -> None:
        """
        Stash changes.

        Args:
            message: Optional stash message

        Raises:
            GitOperationError: On failure
        """
        args = ["stash", "push"]

        if message:
            args.extend(["-m", message])

        self._run_git(args)
        logger.debug("Stashed changes")

    def stash_pop(self) -> None:
        """
        Pop stashed changes.

        Raises:
            GitOperationError: On failure
        """
        self._run_git(["stash", "pop"])
        logger.debug("Popped stash")

    def configure(self, key: str, value: str, global_config: bool = False) -> None:
        """
        Set git configuration.

        Args:
            key: Configuration key
            value: Configuration value
            global_config: Whether to set globally

        Raises:
            GitOperationError: On failure
        """
        args = ["config"]

        if global_config:
            args.append("--global")

        args.extend([key, value])

        self._run_git(args)
        logger.debug(f"Set config {key}={value}")

    def get_config(self, key: str) -> str | None:
        """
        Get git configuration value.

        Args:
            key: Configuration key

        Returns:
            Configuration value or None
        """
        try:
            result = self._run_git(["config", "--get", key], check=False)
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None

    def diff(
        self,
        staged: bool = False,
        file_path: str | None = None,
    ) -> str:
        """
        Get diff output.

        Args:
            staged: Whether to show staged changes
            file_path: Specific file to diff

        Returns:
            Diff output string

        Raises:
            GitOperationError: On failure
        """
        args = ["diff"]

        if staged:
            args.append("--staged")

        if file_path:
            args.append(file_path)

        result = self._run_git(args)
        return result.stdout

    def log(
        self,
        limit: int = 10,
        format_string: str = "%h %s",
    ) -> list[str]:
        """
        Get commit log.

        Args:
            limit: Maximum commits to return
            format_string: Git log format string

        Returns:
            List of formatted commit strings

        Raises:
            GitOperationError: On failure
        """
        args = ["log", f"-{limit}", f"--format={format_string}"]
        result = self._run_git(args)

        if not result.stdout.strip():
            return []

        return result.stdout.strip().split("\n")
