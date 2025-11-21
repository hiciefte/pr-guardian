# GitHub API Contract: PR Guardian

**Phase**: 1 (Design)
**Date**: 2025-10-24
**Status**: Complete
**Feature**: [spec.md](../spec.md) | [plan.md](../plan.md)

## Overview

This document defines the GitHub REST API interaction patterns for PR Guardian, including endpoint specifications, request/response schemas, error handling, rate limit compliance, and retry logic. All API interactions use GitHub CLI (gh) as the primary interface.

---

## Authentication

### Token Requirements

**Token Type**: Personal Access Token (PAT) or Fine-Grained PAT

**Required Scopes**:
- `repo`: Full control of private repositories (for PR access, comments, commits)
- `write:discussion`: Create and edit PR comments

**Token Storage**:
```bash
# Environment variable (runtime mounting)
export GH_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxx"

# Docker Compose
environment:
  - GH_TOKEN=${GH_TOKEN}
```

### Authentication Verification

**Endpoint**: `gh auth status`

**Request**:
```bash
gh auth status
```

**Success Response**:
```
✓ Logged in to github.com as pr-guardian-bot (oauth_token)
✓ Git operations for github.com configured to use https protocol.
✓ Token: *******************
```

**Error Response**:
```
✗ You are not logged into any GitHub hosts. Run gh auth login to authenticate.
```

**Contract**:
- Must verify authentication before any API operations
- Exit with error code 1 if authentication fails
- Log token type and username (redact token value)

---

## Rate Limiting

### Rate Limit Strategy

GitHub REST API limits:
- **Authenticated**: 5,000 requests/hour
- **Secondary**: 100 requests/minute per endpoint

**Rate Limit Headers** (available in gh CLI output):
```
X-RateLimit-Limit: 5000
X-RateLimit-Remaining: 4999
X-RateLimit-Reset: 1698765432
X-RateLimit-Used: 1
```

### Exponential Backoff Implementation

```python
import time
import random
import subprocess

def gh_api_call_with_retry(
    command: list[str],
    max_attempts: int = 5,
    base_wait: float = 1.0
) -> dict:
    """
    Execute gh CLI command with exponential backoff retry.

    Args:
        command: gh CLI command as list (e.g., ["gh", "pr", "list"])
        max_attempts: Maximum retry attempts (default: 5)
        base_wait: Base wait time in seconds (default: 1.0)

    Returns:
        Parsed JSON response from gh CLI

    Raises:
        Exception: If max attempts exceeded or non-retryable error
    """
    for attempt in range(max_attempts):
        result = subprocess.run(
            command,
            capture_output=True,
            text=True
        )

        # Success
        if result.returncode == 0:
            return json.loads(result.stdout) if result.stdout else {}

        # Detect rate limit
        if "rate limit" in result.stderr.lower() or "403" in result.stderr:
            if attempt < max_attempts - 1:
                # Exponential backoff with jitter
                wait_time = (base_wait * (2 ** attempt)) + random.uniform(0, 1)
                logging.warning(f"Rate limit hit, waiting {wait_time:.2f}s (attempt {attempt + 1}/{max_attempts})")
                time.sleep(wait_time)
                continue

        # Non-retryable error
        error_type = parse_gh_error(result.returncode, result.stderr)
        if not error_type.get("retryable", False):
            raise Exception(f"Non-retryable gh CLI error: {result.stderr}")

        # Retryable error (network, server 5xx)
        if attempt < max_attempts - 1:
            wait_time = (base_wait * (2 ** attempt)) + random.uniform(0, 1)
            logging.warning(f"Retryable error, waiting {wait_time:.2f}s (attempt {attempt + 1}/{max_attempts})")
            time.sleep(wait_time)
            continue

    raise Exception(f"Max retry attempts ({max_attempts}) exceeded")
```

---

## Pull Request Discovery

### List Pull Requests

**Endpoint**: `gh pr list`

**Request**:
```bash
gh pr list \
  --repo owner/repository \
  --author translation-bot \
  --state open \
  --json number,title,state,createdAt,updatedAt,headRefName,baseRefName,url \
  --limit 100
```

**Response Schema**:
```json
[
  {
    "number": 868,
    "title": "Update Spanish and German translations",
    "state": "OPEN",
    "createdAt": "2024-10-15T10:30:00Z",
    "updatedAt": "2024-10-16T14:20:00Z",
    "headRefName": "translations-update-2024-10-15",
    "baseRefName": "main",
    "url": "https://github.com/bisq-network/bisq-mobile/pull/868"
  }
]
```

**Field Mapping**:
```python
def map_gh_pr_to_entity(gh_pr: dict) -> TranslationPullRequest:
    """Map gh CLI PR response to TranslationPullRequest entity."""
    return TranslationPullRequest(
        number=gh_pr["number"],
        author=config.target_username,  # Filter ensures match
        title=gh_pr["title"],
        created_at=datetime.fromisoformat(gh_pr["createdAt"].replace("Z", "+00:00")),
        updated_at=datetime.fromisoformat(gh_pr["updatedAt"].replace("Z", "+00:00")),
        state=gh_pr["state"].lower(),
        source_branch=gh_pr["headRefName"],
        target_branch=gh_pr["baseRefName"],
        repository=repository_target,
        url=gh_pr["url"],
        translation_files=[],  # Populated by file list call
        comments=[]  # Populated by comment retrieval
    )
```

**Error Handling**:
```python
def handle_pr_list_errors(result: subprocess.CompletedProcess):
    """Handle errors from gh pr list command."""
    if "not found" in result.stderr.lower():
        raise RepositoryNotFoundError(f"Repository not accessible: {result.stderr}")
    if "permission" in result.stderr.lower():
        raise PermissionError(f"Insufficient permissions: {result.stderr}")
    if result.returncode != 0:
        raise Exception(f"Failed to list PRs: {result.stderr}")
```

### Get PR Files

**Endpoint**: `gh pr view`

**Request**:
```bash
gh pr view 868 \
  --repo owner/repository \
  --json files
```

**Response Schema**:
```json
{
  "files": [
    {
      "path": "src/i18n/es_ES.json",
      "additions": 5,
      "deletions": 3
    },
    {
      "path": "src/i18n/de_DE.json",
      "additions": 8,
      "deletions": 2
    }
  ]
}
```

**Translation File Filtering**:
```python
def filter_translation_files(pr_files: list[dict], patterns: list[str]) -> list[str]:
    """Filter PR files to only translation files."""
    import fnmatch

    translation_files = []
    for file in pr_files:
        file_path = file["path"]
        # Check against translation patterns
        if any(fnmatch.fnmatch(file_path, pattern) for pattern in patterns):
            translation_files.append(file_path)

    return translation_files
```

---

## Comment Retrieval

### Get PR Comments

**Endpoint**: `gh pr view` (with comments)

**Request**:
```bash
gh pr view 868 \
  --repo owner/repository \
  --json comments
```

**Response Schema**:
```json
{
  "comments": [
    {
      "id": "IC_kwDOABCDEF4ABCDEF",
      "author": {
        "login": "coderabbitai"
      },
      "body": "nitpick: Consider using 'Hola' instead of 'Saludo' for a more natural greeting in Spanish.",
      "createdAt": "2024-10-16T08:15:00Z",
      "isMinimized": false
    }
  ]
}
```

### Get PR Review Comments

**Endpoint**: `gh api`

**Request**:
```bash
gh api \
  repos/owner/repository/pulls/868/comments \
  --jq '.[] | {id, user: .user.login, body, created_at: .created_at, path, line: .line, diff_hunk}'
```

**Response Schema**:
```json
[
  {
    "id": 1234567890,
    "user": "coderabbitai",
    "body": "suggestion: Change {usuario} to {user} to match source key",
    "created_at": "2024-10-16T09:00:00Z",
    "path": "src/i18n/es_ES.json",
    "line": 42,
    "diff_hunk": "@@ -40,7 +40,7 @@\n \"welcome\": \"Bienvenido\",\n-\"greeting\": \"Saludo\"\n+\"greeting\": \"Hola\""
  }
]
```

### Combined Comment Retrieval

```python
def retrieve_all_comments(
    repo_owner: str,
    repo_name: str,
    pr_number: int
) -> list[ReviewComment]:
    """
    Retrieve both issue comments and review comments for PR.

    Returns unified list of ReviewComment entities.
    """
    comments = []

    # Get issue comments (general PR comments)
    issue_comments_result = subprocess.run(
        ["gh", "pr", "view", str(pr_number),
         "--repo", f"{repo_owner}/{repo_name}",
         "--json", "comments"],
        capture_output=True,
        text=True
    )
    issue_comments_data = json.loads(issue_comments_result.stdout)

    for comment in issue_comments_data.get("comments", []):
        if comment["author"]["login"].lower() == "coderabbitai":
            comments.append(ReviewComment(
                id=int(comment["id"].split("_")[-1], 36),  # Convert ID
                author=comment["author"]["login"],
                body=comment["body"],
                created_at=datetime.fromisoformat(comment["createdAt"].replace("Z", "+00:00")),
                file_path=None,
                line_number=None,
                diff_hunk=None,
                conventional_label=extract_label(comment["body"]),
                pull_request=pr,
                classification=None,
                is_actionable=None
            ))

    # Get review comments (line-specific comments)
    review_comments_result = subprocess.run(
        ["gh", "api", f"repos/{repo_owner}/{repo_name}/pulls/{pr_number}/comments",
         "--jq", '.[] | {id, user: .user.login, body, created_at: .created_at, path, line: .line, diff_hunk}'],
        capture_output=True,
        text=True
    )

    for line in review_comments_result.stdout.strip().split("\n"):
        if not line:
            continue
        comment_data = json.loads(line)

        if comment_data["user"].lower() == "coderabbitai":
            comments.append(ReviewComment(
                id=comment_data["id"],
                author=comment_data["user"],
                body=comment_data["body"],
                created_at=datetime.fromisoformat(comment_data["created_at"].replace("Z", "+00:00")),
                file_path=comment_data.get("path"),
                line_number=comment_data.get("line"),
                diff_hunk=comment_data.get("diff_hunk"),
                conventional_label=extract_label(comment_data["body"]),
                pull_request=pr,
                classification=None,
                is_actionable=None
            ))

    return comments
```

---

## Comment Posting

### Post PR Comment

**Endpoint**: `gh pr comment`

**Request**:
```bash
gh pr comment 868 \
  --repo owner/repository \
  --body "$(cat <<'EOF'
## PR Guardian Implementation Summary

| Locale | Comment Type | Classification | Implemented | Reasoning |
|--------|-------------|----------------|-------------|-----------|
| es_ES | Nitpick | Translation Nitpick | ✅ Yes | Natural greeting improvement |
| de_DE | Suggestion | Constructive | ✅ Yes | Punctuation consistency |

**Total Comments Processed**: 18
**Changes Implemented**: 15
**Commits Created**: 15

🤖 Generated by PR Guardian
EOF
)"
```

**Success Response**:
```
https://github.com/owner/repository/pull/868#issuecomment-12345678
```

**Request Schema** (Python):
```python
def post_pr_summary_comment(
    repo_owner: str,
    repo_name: str,
    pr_number: int,
    summary: SessionReport
) -> str:
    """
    Post implementation summary comment to PR.

    Returns: Comment URL
    """
    # Build markdown table
    table_rows = []
    for change in summary.changes_implemented:
        table_rows.append(
            f"| {change.locale} | {change.classification_type} | "
            f"{'✅ Yes' if change.validated else '❌ No'} | "
            f"{change.validation_error or 'Implemented successfully'} |"
        )

    body = f"""## PR Guardian Implementation Summary

| Locale | Classification | Implemented | Status |
|--------|----------------|-------------|--------|
{''.join(table_rows)}

**Total Comments Processed**: {summary.comments_total}
**Changes Implemented**: {summary.changes_implemented}
**Commits Created**: {summary.commits_created}

🤖 Generated by PR Guardian | Session: {summary.session_id}
"""

    # Post comment via gh CLI
    result = subprocess.run(
        ["gh", "pr", "comment", str(pr_number),
         "--repo", f"{repo_owner}/{repo_name}",
         "--body", body],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise Exception(f"Failed to post comment: {result.stderr}")

    return result.stdout.strip()
```

---

## Commit Operations (via Git + GitHub API)

### Commit Signing with Web-Flow

**Endpoint**: `gh api` (Git Data API)

**Create Tree**:
```bash
gh api \
  repos/owner/repository/git/trees \
  -f base_tree="BASE_TREE_SHA" \
  -f "tree[][path]=src/i18n/es_ES.json" \
  -f "tree[][mode]=100644" \
  -f "tree[][type]=blob" \
  -f "tree[][content]=FILE_CONTENT"
```

**Response**:
```json
{
  "sha": "NEW_TREE_SHA",
  "url": "https://api.github.com/repos/owner/repository/git/trees/NEW_TREE_SHA"
}
```

**Create Commit**:
```bash
gh api \
  repos/owner/repository/git/commits \
  -f message="Update Spanish translation: greeting formality

What: Changed 'Saludo' to 'Hola' for more natural greeting
Why: CodeRabbitAI nitpick for localization consistency with
     informal Spanish usage patterns
CodeRabbitAI-Comment-ID: 1234567890
Locale: es_ES" \
  -f tree="NEW_TREE_SHA" \
  -f "parents[]=PARENT_COMMIT_SHA"
```

**Response**:
```json
{
  "sha": "NEW_COMMIT_SHA",
  "url": "https://api.github.com/repos/owner/repository/git/commits/NEW_COMMIT_SHA",
  "author": {
    "name": "pr-guardian-bot",
    "email": "noreply@github.com",
    "date": "2024-10-16T14:30:00Z"
  },
  "committer": {
    "name": "GitHub",
    "email": "noreply@github.com",
    "date": "2024-10-16T14:30:00Z"
  },
  "message": "Update Spanish translation: greeting formality\n\nWhat: Changed...",
  "verification": {
    "verified": true,
    "reason": "valid",
    "signature": "-----BEGIN PGP SIGNATURE-----...",
    "payload": "..."
  }
}
```

### Update Branch Reference

**Endpoint**: `gh api` (update ref)

**Request**:
```bash
gh api \
  repos/owner/repository/git/refs/heads/branch-name \
  -X PATCH \
  -f sha="NEW_COMMIT_SHA" \
  -F force=false
```

**Response**:
```json
{
  "ref": "refs/heads/branch-name",
  "node_id": "MDM6UmVmMTI...",
  "url": "https://api.github.com/repos/owner/repository/git/refs/heads/branch-name",
  "object": {
    "type": "commit",
    "sha": "NEW_COMMIT_SHA",
    "url": "https://api.github.com/repos/owner/repository/git/commits/NEW_COMMIT_SHA"
  }
}
```

### Commit Verification

**Endpoint**: `gh api` (get commit)

**Request**:
```bash
gh api \
  repos/owner/repository/commits/NEW_COMMIT_SHA \
  --jq '.commit.verification'
```

**Response**:
```json
{
  "verified": true,
  "reason": "valid",
  "signature": "-----BEGIN PGP SIGNATURE-----\n...",
  "payload": "tree NEW_TREE_SHA\nparent PARENT_SHA\nauthor..."
}
```

**Verification States**:
| Reason | Verified | Description |
|--------|----------|-------------|
| `valid` | true | Signature verified successfully |
| `invalid` | false | Signature invalid |
| `expired_key` | false | Signing key expired |
| `unknown_signature_type` | false | Unsupported signature type |
| `unsigned` | false | Commit not signed |

---

## Issue Creation (Feedback)

### Create Issue

**Endpoint**: `gh issue create`

**Request**:
```bash
gh issue create \
  --repo owner/translation-automation \
  --title "Translation Feedback - Session 20241016" \
  --label "translation-feedback,automated,pr-guardian" \
  --body "$(cat <<'EOF'
# Translation Feedback - Session session_20241016_023000_a1b2c3d4

**Session Date**: 2024-10-16
**Repositories Processed**: bisq-network/bisq-mobile, bisq-network/bisq2
**PRs Analyzed**: 2
**Comments Reviewed**: 18

## Summary

Identified 3 recurring terminology inconsistencies across Spanish locales.

## Patterns Identified

### Pattern 1: terminology (moderate)
- **Frequency**: 8 occurrences
- **Affected Locales**: es_ES, es_MX, es_AR
- **Examples**:
  - Inconsistent 'Login' vs 'Iniciar sesión' across Spanish locales
- **Recommendation**: Update translation glossary

---

🤖 Generated by PR Guardian | Session: session_20241016_023000_a1b2c3d4
EOF
)"
```

**Success Response**:
```
https://github.com/owner/translation-automation/issues/456
```

**Request Schema** (Python):
```python
def create_feedback_issue(
    feedback_repo: str,
    session: SessionReport,
    patterns: list[FeedbackPattern]
) -> FeedbackIssue:
    """
    Create feedback issue in configured repository.

    Args:
        feedback_repo: Repository identifier (owner/repo)
        session: Session report
        patterns: Feedback patterns to include

    Returns:
        FeedbackIssue entity with GitHub issue number and URL
    """
    # Build issue body
    body = generate_feedback_issue_body(session, patterns)

    # Create issue via gh CLI
    result = subprocess.run(
        [
            "gh", "issue", "create",
            "--repo", feedback_repo,
            "--title", f"Translation Feedback - Session {session.start_time.strftime('%Y%m%d')}",
            "--label", "translation-feedback,automated,pr-guardian",
            "--body", body
        ],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise Exception(f"Failed to create feedback issue: {result.stderr}")

    # Extract issue URL and number
    issue_url = result.stdout.strip()
    issue_number = int(issue_url.split("/")[-1])

    return FeedbackIssue(
        issue_number=issue_number,
        title=f"Translation Feedback - Session {session.start_time.strftime('%Y%m%d')}",
        body=body,
        created_at=datetime.now(timezone.utc),
        repository=feedback_repo,
        url=issue_url,
        session=session,
        patterns=patterns,
        labels=["translation-feedback", "automated", "pr-guardian"]
    )
```

---

## Error Handling Patterns

### Error Classification

```python
def parse_gh_error(exit_code: int, stderr: str) -> dict:
    """
    Parse gh CLI error for type and retryability.

    Returns:
        {
            "type": str,          # Error type classification
            "retryable": bool,    # Whether error is retryable
            "message": str        # Human-readable error message
        }
    """
    # Exit code classification
    error_types = {
        1: "general_error",
        2: "usage_error",
        3: "authentication_error",
        4: "not_found_error"
    }

    # HTTP status extraction
    http_match = re.search(r"HTTP (\d{3})", stderr)
    if http_match:
        status_code = int(http_match.group(1))

        # Rate limiting
        if status_code == 403 and "rate limit" in stderr.lower():
            return {
                "type": "rate_limit",
                "retryable": True,
                "message": "GitHub API rate limit exceeded"
            }

        # Not found
        if status_code == 404:
            return {
                "type": "not_found",
                "retryable": False,
                "message": f"Resource not found: {extract_resource(stderr)}"
            }

        # Server errors (retryable)
        if status_code >= 500:
            return {
                "type": "server_error",
                "retryable": True,
                "message": f"GitHub server error ({status_code})"
            }

    # Keyword-based detection
    stderr_lower = stderr.lower()

    if "not found" in stderr_lower:
        return {"type": "not_found", "retryable": False, "message": stderr}

    if "permission" in stderr_lower or "forbidden" in stderr_lower:
        return {"type": "permission", "retryable": False, "message": stderr}

    if "authentication" in stderr_lower or "401" in stderr:
        return {"type": "authentication", "retryable": False, "message": stderr}

    if "network" in stderr_lower or "timeout" in stderr_lower:
        return {"type": "network", "retryable": True, "message": stderr}

    # Default classification
    return {
        "type": error_types.get(exit_code, "unknown"),
        "retryable": False,
        "message": stderr
    }
```

### Retry Strategy

```python
RETRYABLE_ERROR_TYPES = [
    "rate_limit",
    "server_error",
    "network"
]

def should_retry_error(error: dict) -> bool:
    """Determine if error should trigger retry."""
    return error.get("retryable", False) and error["type"] in RETRYABLE_ERROR_TYPES
```

---

## Contract Tests

### Test Suite Structure

```python
# tests/contract/test_github_api.py

def test_gh_authentication():
    """Verify gh CLI authentication works."""
    result = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "Logged in" in result.stdout

def test_gh_pr_list_contract():
    """Verify gh pr list returns expected JSON structure."""
    result = subprocess.run(
        ["gh", "pr", "list", "--json", "number,title,state", "--limit", "1"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0

    prs = json.loads(result.stdout)
    assert isinstance(prs, list)

    if prs:
        pr = prs[0]
        assert "number" in pr
        assert "title" in pr
        assert "state" in pr

def test_gh_pr_view_comments_contract():
    """Verify gh pr view --json comments returns expected structure."""
    # Assumes test PR exists
    result = subprocess.run(
        ["gh", "pr", "view", "1", "--json", "comments"],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        data = json.loads(result.stdout)
        assert "comments" in data
        assert isinstance(data["comments"], list)

def test_gh_api_rate_limit_headers():
    """Verify gh api includes rate limit information."""
    result = subprocess.run(
        ["gh", "api", "rate_limit"],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0
    rate_limit = json.loads(result.stdout)
    assert "resources" in rate_limit
    assert "core" in rate_limit["resources"]
    assert "limit" in rate_limit["resources"]["core"]
    assert "remaining" in rate_limit["resources"]["core"]
```

---

## Performance Considerations

### API Call Budgets

For PR Guardian execution processing 3 repositories with 10 PRs total:

| Operation | Calls per PR | Total Calls | Notes |
|-----------|--------------|-------------|-------|
| List PRs | 1 per repo | 3 | One-time per repository |
| Get PR files | 1 per PR | 10 | One per discovered PR |
| Get comments | 2 per PR | 20 | Issue comments + review comments |
| Get tree | 1 per commit | ~15 | For Web-Flow signing |
| Create commit | 1 per change | ~15 | Atomic commits |
| Update ref | 1 per commit | ~15 | Push commits |
| Post comment | 1 per PR | 10 | Summary comment |
| Create issue | 1 per session | 1 | Feedback issue |

**Total**: ~89 API calls per session
**Rate Limit Usage**: <2% of hourly limit (5,000 requests)

### Optimization Strategies

1. **Batch Operations**: Minimize API calls by batching where possible
2. **Parallel Processing**: Process multiple repositories concurrently (respects rate limits)
3. **Caching**: Cache PR data for session duration (30-minute execution window)
4. **Incremental Processing**: Skip already-processed PRs via timestamp tracking

---

## Security Considerations

### Token Security

- **Storage**: Environment variables, Docker secrets, never in code
- **Logging**: Redact tokens from all logs and error messages
- **Transmission**: HTTPS only (enforced by gh CLI)
- **Rotation**: Support token refresh without code changes

### API Safety

- **Read-Only Default**: Minimize write operations
- **Validation**: Verify all API responses before processing
- **Atomic Operations**: Commit operations are atomic (all-or-nothing)
- **Rollback**: Failed commits can be rolled back via git reset

### Rate Limit Compliance

- **Respect Limits**: Never intentionally bypass rate limits
- **Exponential Backoff**: Required retry pattern for rate limit errors
- **Monitoring**: Track API usage per session
- **Abort on Exhaustion**: Fail gracefully if rate limit exhausted

---

## Summary

This contract defines comprehensive GitHub API interaction patterns for PR Guardian, ensuring:
- **Reliability**: Exponential backoff retry for transient failures
- **Compliance**: Rate limit respect and proper error handling
- **Security**: Token protection and validation
- **Performance**: Optimized API usage (<2% of rate limit per session)
- **Testability**: Contract tests validate API assumptions

**Next Steps**: Create quickstart guide and update agent context to complete Phase 1.
