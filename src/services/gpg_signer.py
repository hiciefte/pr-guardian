"""GPG Signing Service for commit signing."""

import json
import logging
import os
import subprocess
from pathlib import Path

from src.services.github_client import GitHubClient

logger = logging.getLogger(__name__)


class GPGSigningError(Exception):
    """Raised when GPG signing fails."""
    pass


class GPGSigner:
    """
    GPG signing service supporting web-flow and traditional GPG.

    Provides methods for signing commits using either GitHub's
    web-flow signing or local GPG keys.
    """

    def __init__(
        self,
        gpg_key_id: str | None = None,
        github_client: GitHubClient | None = None,
        repo_path: Path | None = None,
    ):
        """
        Initialize GPG signer.

        Args:
            gpg_key_id: GPG key ID for local signing
            github_client: GitHub client for web-flow signing
            repo_path: Repository path for git operations
        """
        self.gpg_key_id = gpg_key_id or os.getenv("GPG_KEY_ID")
        self.github_client = github_client
        self.repo_path = repo_path or Path.cwd()

    def sign_commit_webflow(
        self,
        message: str,
        files: list[str],
        branch: str,
        owner: str,
        repo: str,
    ) -> str:
        """
        Create a signed commit using GitHub's web-flow.

        Uses GitHub API to create commits, which are signed by GitHub.
        Requires a GitHub token with appropriate permissions.

        Args:
            message: Commit message
            files: List of file paths to include
            branch: Branch to commit to
            owner: Repository owner
            repo: Repository name

        Returns:
            Created commit SHA

        Raises:
            GPGSigningError: On signing failure
        """
        if not self.github_client:
            raise GPGSigningError("GitHub client required for web-flow signing")

        try:
            # Get current commit SHA for parent
            result = self.github_client._run_gh_command([
                "api",
                f"repos/{owner}/{repo}/git/ref/heads/{branch}",
            ])
            ref_data = json.loads(result.stdout)
            parent_sha = ref_data["object"]["sha"]

            # Get parent tree
            result = self.github_client._run_gh_command([
                "api",
                f"repos/{owner}/{repo}/git/commits/{parent_sha}",
            ])
            commit_data = json.loads(result.stdout)
            base_tree_sha = commit_data["tree"]["sha"]

            # Create tree with updated files
            tree_items = []
            for file_path in files:
                full_path = self.repo_path / file_path
                if not full_path.exists():
                    logger.warning(f"File not found, skipping: {file_path}")
                    continue

                content = full_path.read_text()

                # Create blob
                blob_result = self.github_client._run_gh_command([
                    "api",
                    f"repos/{owner}/{repo}/git/blobs",
                    "-X", "POST",
                    "-f", f"content={content}",
                    "-f", "encoding=utf-8",
                ])
                blob_data = json.loads(blob_result.stdout)

                tree_items.append({
                    "path": file_path,
                    "mode": "100644",
                    "type": "blob",
                    "sha": blob_data["sha"],
                })

            # Check if any files were found
            if not tree_items and files:
                logger.error("No valid files found for commit")
                raise GPGSigningError("No valid files to commit")

            # Create tree
            tree_json = json.dumps(tree_items)
            tree_result = self.github_client._run_gh_command([
                "api",
                f"repos/{owner}/{repo}/git/trees",
                "-X", "POST",
                "-f", f"base_tree={base_tree_sha}",
                "--raw-field", f"tree={tree_json}",
            ])
            tree_data = json.loads(tree_result.stdout)

            # Create commit
            commit_result = self.github_client._run_gh_command([
                "api",
                f"repos/{owner}/{repo}/git/commits",
                "-X", "POST",
                "-f", f"message={message}",
                "-f", f"tree={tree_data['sha']}",
                "--raw-field", f"parents=[\"{parent_sha}\"]",
            ])
            new_commit = json.loads(commit_result.stdout)
            commit_sha = new_commit["sha"]

            # Update branch reference
            self.github_client._run_gh_command([
                "api",
                f"repos/{owner}/{repo}/git/refs/heads/{branch}",
                "-X", "PATCH",
                "-f", f"sha={commit_sha}",
            ])

            logger.info(f"Created web-flow signed commit: {commit_sha[:8]}")
            return commit_sha

        except Exception as e:
            raise GPGSigningError(f"Web-flow signing failed: {e}") from e

    def sign_commit_gpg(
        self,
        message: str,
    ) -> str:
        """
        Create a signed commit using local GPG.

        Uses git commit -S with the configured GPG key.

        Args:
            message: Commit message

        Returns:
            Commit SHA

        Raises:
            GPGSigningError: On signing failure
        """
        if not self.gpg_key_id:
            raise GPGSigningError(
                "GPG key ID required. Set GPG_KEY_ID environment variable."
            )

        try:
            # Configure git to use the GPG key
            subprocess.run(
                ["git", "config", "user.signingkey", self.gpg_key_id],
                cwd=self.repo_path,
                check=True,
                capture_output=True,
            )

            # Create signed commit
            result = subprocess.run(
                ["git", "commit", "-S", "-m", message],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                raise GPGSigningError(
                    f"Commit failed: {result.stderr.strip()}"
                )

            # Get commit SHA
            sha_result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )

            sha = sha_result.stdout.strip()
            logger.info(f"Created GPG signed commit: {sha[:8]}")
            return sha

        except subprocess.CalledProcessError as e:
            raise GPGSigningError(
                f"GPG signing failed: {e.stderr if hasattr(e, 'stderr') else str(e)}"
            ) from e

    def verify_signature(self, commit_sha: str) -> bool:
        """
        Verify a commit's GPG signature.

        Args:
            commit_sha: Commit SHA to verify

        Returns:
            True if signature is valid
        """
        try:
            result = subprocess.run(
                ["git", "verify-commit", commit_sha],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                logger.debug(f"Signature valid for {commit_sha[:8]}")
                return True

            # Check stderr for signature info
            if "Good signature" in result.stderr:
                return True

            logger.warning(
                f"Signature verification failed for {commit_sha[:8]}: "
                f"{result.stderr.strip()}"
            )
            return False

        except Exception:
            logger.exception("Verification error")
            return False

    def get_signature_info(self, commit_sha: str) -> dict | None:
        """
        Get signature information for a commit.

        Args:
            commit_sha: Commit SHA

        Returns:
            Dict with signature info or None
        """
        try:
            result = subprocess.run(
                [
                    "git", "log", "-1",
                    "--format=%G?|%GS|%GK",
                    commit_sha,
                ],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )

            parts = result.stdout.strip().split("|")
            if len(parts) < 3:
                return None

            status_map = {
                "G": "good",
                "B": "bad",
                "U": "unknown_validity",
                "X": "expired",
                "Y": "expired_key",
                "R": "revoked",
                "E": "cannot_check",
                "N": "no_signature",
            }

            return {
                "status": status_map.get(parts[0], "unknown"),
                "signer": parts[1] if parts[1] else None,
                "key_id": parts[2] if parts[2] else None,
            }

        except Exception:
            logger.exception("Failed to get signature info")
            return None

    def is_gpg_available(self) -> bool:
        """
        Check if GPG is available on the system.

        Returns:
            True if GPG is available
        """
        try:
            result = subprocess.run(
                ["gpg", "--version"],
                capture_output=True,
                text=True,
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False

    def list_keys(self) -> list[dict]:
        """
        List available GPG keys.

        Returns:
            List of key info dicts
        """
        try:
            result = subprocess.run(
                [
                    "gpg", "--list-secret-keys",
                    "--keyid-format=long",
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            keys: list[dict] = []
            lines = result.stdout.split("\n")

            current_key: dict = {}
            for line in lines:
                if line.startswith("sec"):
                    if current_key:
                        keys.append(current_key)

                    # Parse key info: sec   rsa4096/KEYID 2024-01-01
                    parts = line.split()
                    if len(parts) >= 2:
                        key_part = parts[1]
                        if "/" in key_part:
                            key_id = key_part.split("/")[1]
                            current_key = {"key_id": key_id}

                elif line.startswith("uid") and current_key:
                    # Parse uid: uid [ultimate] Name <email>
                    uid_part = line[3:].strip()
                    # Remove trust level
                    if "]" in uid_part:
                        uid_part = uid_part.split("]")[1].strip()
                    current_key["uid"] = uid_part

            if current_key:
                keys.append(current_key)

            return keys

        except Exception:
            logger.exception("Failed to list GPG keys")
            return []

    def import_key(self, key_data: str) -> bool:
        """
        Import a GPG key.

        Args:
            key_data: ASCII-armored GPG key

        Returns:
            True if import successful
        """
        try:
            result = subprocess.run(
                ["gpg", "--import"],
                input=key_data,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                logger.info("GPG key imported successfully")
                return True

            logger.error(f"GPG import failed: {result.stderr}")
            return False

        except Exception:
            logger.exception("Failed to import GPG key")
            return False


def configure_git_signing(
    repo_path: Path,
    gpg_key_id: str,
    user_name: str,
    user_email: str,
) -> None:
    """
    Configure git for GPG signing.

    Args:
        repo_path: Repository path
        gpg_key_id: GPG key ID to use
        user_name: Git user name
        user_email: Git user email

    Raises:
        GPGSigningError: On configuration failure
    """
    configs = [
        ("user.name", user_name),
        ("user.email", user_email),
        ("user.signingkey", gpg_key_id),
        ("commit.gpgsign", "true"),
        ("gpg.program", "gpg"),
    ]

    for key, value in configs:
        try:
            subprocess.run(
                ["git", "config", "--local", key, value],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as e:
            raise GPGSigningError(
                f"Failed to configure {key}: {e.stderr if hasattr(e, 'stderr') else str(e)}"
            ) from e

    logger.info(f"Configured git signing with key {gpg_key_id}")
