# Data Model: PR Guardian

**Phase**: 1 (Design)
**Date**: 2025-10-24
**Status**: Complete
**Feature**: [spec.md](./spec.md) | [plan.md](./plan.md)

## Overview

This document defines the 11 key entities for PR Guardian, extracted from the feature specification. Each entity includes fields, relationships, validation rules, and state transitions where applicable.

**Note**: Entity 5 (Translation Extraction) was added on 2025-10-24 to support LLM-based natural language comment parsing with Claude 3 Haiku.

---

## Entity 1: PR Guardian Configuration

**Purpose**: Represents the agent's runtime configuration including monitored repositories, execution settings, and authentication details.

### Fields

| Field | Type | Required | Description | Validation Rules |
|-------|------|----------|-------------|------------------|
| `github_token` | `str` | Yes | GitHub authentication token | Non-empty, starts with "ghp_" or "github_pat_" |
| `monitored_repositories` | `list[RepositoryTarget]` | Yes | List of repositories to monitor | 1-10 repositories |
| `target_username` | `str` | Yes | GitHub username to monitor for PRs | Non-empty, valid GitHub username format |
| `schedule_cron` | `str` | Yes | Cron expression for execution schedule | Valid cron format (e.g., "0 2 * * *") |
| `gpg_key_path` | `str` | Yes | Path to GPG bot key for signing | Absolute path, file must exist |
| `deploy_key_path` | `str` | Yes | Path to SSH deploy key | Absolute path, file must exist with 600 permissions |
| `feedback_repository` | `str` | No | Repository for feedback issues (owner/repo) | Format: "owner/repository" |
| `max_comments_per_pr` | `int` | No | Maximum comments to process per PR | Default: 50, Range: 1-100 |
| `execution_timeout_seconds` | `int` | No | Maximum execution time in seconds | Default: 1800 (30 min), Range: 60-3600 |
| `log_level` | `str` | No | Logging verbosity | Enum: "DEBUG", "INFO", "WARNING", "ERROR", Default: "INFO" |

### Relationships

- **Has Many** `RepositoryTarget`: Configuration specifies 1-10 repositories to monitor
- **References** `FeedbackIssue`: Feedback issues created in configured feedback repository

### Validation Rules

```python
def validate_configuration(config: PRGuardianConfiguration) -> tuple[bool, list[str]]:
    """Validate configuration integrity."""
    errors = []

    # Repository count
    if not (1 <= len(config.monitored_repositories) <= 10):
        errors.append("Must monitor between 1 and 10 repositories")

    # GitHub token format
    if not (config.github_token.startswith("ghp_") or
            config.github_token.startswith("github_pat_")):
        errors.append("Invalid GitHub token format")

    # Deploy key permissions
    if os.path.exists(config.deploy_key_path):
        stat_info = os.stat(config.deploy_key_path)
        if stat_info.st_mode & 0o777 != 0o600:
            errors.append(f"Deploy key must have 600 permissions (current: {oct(stat_info.st_mode)[-3:]})")

    # GPG key existence
    if not os.path.exists(config.gpg_key_path):
        errors.append(f"GPG key not found at {config.gpg_key_path}")

    # Cron expression validation
    try:
        croniter(config.schedule_cron)
    except:
        errors.append(f"Invalid cron expression: {config.schedule_cron}")

    return len(errors) == 0, errors
```

### Example

```python
config = PRGuardianConfiguration(
    github_token="ghp_xxxxxxxxxxxxxxxxxxxx",
    monitored_repositories=[
        RepositoryTarget("bisq-network", "bisq-mobile"),
        RepositoryTarget("bisq-network", "bisq2")
    ],
    target_username="translation-bot",
    schedule_cron="0 2 * * *",  # Daily at 02:00 UTC
    gpg_key_path="/secrets/gpg_bot_key",
    deploy_key_path="/secrets/deploy_key",
    feedback_repository="bisq-network/translation-automation",
    max_comments_per_pr=50,
    execution_timeout_seconds=1800
)
```

---

## Entity 2: Repository Target

**Purpose**: Represents a GitHub repository to monitor with owner name, repository name, and optional repository-specific settings.

### Fields

| Field | Type | Required | Description | Validation Rules |
|-------|------|----------|-------------|------------------|
| `owner` | `str` | Yes | GitHub repository owner | Non-empty, valid GitHub username/org |
| `repository` | `str` | Yes | GitHub repository name | Non-empty, valid repository name |
| `branch_filter` | `str` | No | Only process PRs targeting this branch | Default: None (all branches) |
| `translation_file_patterns` | `list[str]` | No | Custom translation file patterns | Glob patterns, Default: constitution patterns |
| `enabled` | `bool` | No | Whether to process this repository | Default: True |

### Relationships

- **Belongs To** `PRGuardianConfiguration`: Part of configuration's monitored repositories
- **Has Many** `TranslationPullRequest`: PRs discovered in this repository

### Validation Rules

```python
def validate_repository_target(target: RepositoryTarget) -> tuple[bool, list[str]]:
    """Validate repository target configuration."""
    errors = []

    # Owner format (GitHub username/org constraints)
    if not re.match(r'^[a-zA-Z0-9-]+$', target.owner):
        errors.append(f"Invalid owner format: {target.owner}")

    # Repository name format
    if not re.match(r'^[a-zA-Z0-9._-]+$', target.repository):
        errors.append(f"Invalid repository name: {target.repository}")

    # Translation file patterns (if custom)
    if target.translation_file_patterns:
        for pattern in target.translation_file_patterns:
            if not ('*' in pattern or '/' in pattern):
                errors.append(f"Invalid glob pattern: {pattern}")

    return len(errors) == 0, errors
```

### Default Translation Patterns

From constitution principle III:

```python
DEFAULT_TRANSLATION_PATTERNS = [
    "*.properties",
    "**/i18n/**/*.json",
    "**/locales/**/*.yml",
    "**/locales/**/*.yaml",
    "**/lang/**/*"
]
```

### Example

```python
target = RepositoryTarget(
    owner="bisq-network",
    repository="bisq-mobile",
    branch_filter="main",  # Only PRs targeting main branch
    translation_file_patterns=DEFAULT_TRANSLATION_PATTERNS,
    enabled=True
)
```

---

## Entity 3: Translation Pull Request

**Purpose**: Represents a discovered PR with PR number, author username, title, creation date, branch names, file list, current state, and comment collection.

### Fields

| Field | Type | Required | Description | Validation Rules |
|-------|------|----------|-------------|------------------|
| `number` | `int` | Yes | PR number | Positive integer |
| `author` | `str` | Yes | PR author username | Non-empty, valid GitHub username |
| `title` | `str` | Yes | PR title | Non-empty string |
| `created_at` | `datetime` | Yes | PR creation timestamp (UTC) | Timezone-aware datetime |
| `updated_at` | `datetime` | Yes | PR last update timestamp (UTC) | Timezone-aware datetime |
| `state` | `str` | Yes | PR state | Enum: "open", "closed", "merged" |
| `source_branch` | `str` | Yes | Source branch name | Non-empty string |
| `target_branch` | `str` | Yes | Target branch name | Non-empty string |
| `repository` | `RepositoryTarget` | Yes | Repository reference | Valid RepositoryTarget |
| `url` | `str` | Yes | PR URL | Valid GitHub PR URL |
| `translation_files` | `list[str]` | Yes | Translation files modified in PR | Paths matching translation patterns |
| `comments` | `list[ReviewComment]` | Yes | All review and issue comments | Empty or populated list |
| `processed_at` | `datetime` | No | Timestamp when agent processed this PR | Timezone-aware datetime, None if not processed |

### Relationships

- **Belongs To** `RepositoryTarget`: PR discovered in specific repository
- **Has Many** `ReviewComment`: CodeRabbitAI comments on this PR
- **Has Many** `CommitRecord`: Commits created by agent for this PR

### State Transitions

```
[Discovered] → [Processing] → [Completed]
     ↓              ↓              ↓
[Skipped]    [Failed]      [Partially Completed]
```

**State Transition Logic**:
```python
def can_process_pr(pr: TranslationPullRequest) -> tuple[bool, str]:
    """Determine if PR can be processed."""
    # Check state
    if pr.state != "open":
        return False, f"PR state is {pr.state}, must be open"

    # Check author
    if pr.author != config.target_username:
        return False, f"PR author {pr.author} does not match target {config.target_username}"

    # Check translation files
    if not pr.translation_files:
        return False, "PR does not modify any translation files"

    # Check processing status
    if pr.processed_at and (datetime.now(timezone.utc) - pr.processed_at).hours < 24:
        return False, "PR processed within last 24 hours"

    return True, "PR eligible for processing"
```

### Validation Rules

```python
def validate_pull_request(pr: TranslationPullRequest) -> tuple[bool, list[str]]:
    """Validate pull request data integrity."""
    errors = []

    # PR number positive
    if pr.number <= 0:
        errors.append(f"Invalid PR number: {pr.number}")

    # State valid
    if pr.state not in ["open", "closed", "merged"]:
        errors.append(f"Invalid PR state: {pr.state}")

    # Timestamps timezone-aware and UTC
    if pr.created_at.tzinfo != timezone.utc:
        errors.append("created_at must be UTC timezone-aware")
    if pr.updated_at.tzinfo != timezone.utc:
        errors.append("updated_at must be UTC timezone-aware")

    # Translation files match patterns
    for file_path in pr.translation_files:
        if not matches_translation_pattern(file_path):
            errors.append(f"File does not match translation patterns: {file_path}")

    return len(errors) == 0, errors
```

### Example

```python
pr = TranslationPullRequest(
    number=868,
    author="translation-bot",
    title="Update Spanish and German translations",
    created_at=datetime(2024, 10, 15, 10, 30, tzinfo=timezone.utc),
    updated_at=datetime(2024, 10, 16, 14, 20, tzinfo=timezone.utc),
    state="open",
    source_branch="translations-update-2024-10-15",
    target_branch="main",
    repository=RepositoryTarget("bisq-network", "bisq-mobile"),
    url="https://github.com/bisq-network/bisq-mobile/pull/868",
    translation_files=[
        "src/i18n/es_ES.json",
        "src/i18n/de_DE.json"
    ],
    comments=[],  # Populated by comment retrieval service
    processed_at=None
)
```

---

## Entity 4: Review Comment

**Purpose**: Represents a CodeRabbitAI comment with comment ID, author, body text, created timestamp, file path, line number, diff context, conventional comment label, and classification by agent.

### Fields

| Field | Type | Required | Description | Validation Rules |
|-------|------|----------|-------------|------------------|
| `id` | `int` | Yes | GitHub comment ID | Positive integer, unique |
| `author` | `str` | Yes | Comment author username | Must be "coderabbitai" |
| `body` | `str` | Yes | Comment body text | Non-empty string |
| `created_at` | `datetime` | Yes | Comment creation timestamp (UTC) | Timezone-aware datetime |
| `file_path` | `str` | No | File path for review comments | Relative path from repository root |
| `line_number` | `int` | No | Line number in file | Positive integer if file_path exists |
| `diff_hunk` | `str` | No | Diff context around comment | Diff format string |
| `conventional_label` | `str` | No | CodeRabbitAI's label (nitpick, suggestion, etc.) | Enum or free text |
| `pull_request` | `TranslationPullRequest` | Yes | Associated PR | Valid TranslationPullRequest |
| `classification` | `CommentClassification` | No | Agent's classification result | Populated after classification |
| `is_actionable` | `bool` | No | Whether comment requires implementation | Determined by classification |

### Relationships

- **Belongs To** `TranslationPullRequest`: Comment on specific PR
- **Has One** `CommentClassification`: Agent's analysis of this comment
- **References** `TranslationChange`: Changes implemented from this comment

### Comment Types

From CodeRabbitAI conventional labels:
- `nitpick`: Minor improvements
- `suggestion`: Constructive improvements
- `issue`: Critical problems
- `question`: Clarification requests
- `praise`: Positive feedback

### Validation Rules

```python
def validate_review_comment(comment: ReviewComment) -> tuple[bool, list[str]]:
    """Validate review comment data."""
    errors = []

    # Author must be CodeRabbitAI
    if comment.author.lower() != "coderabbitai":
        errors.append(f"Comment author must be 'coderabbitai', got '{comment.author}'")

    # Timestamp must be UTC
    if comment.created_at.tzinfo != timezone.utc:
        errors.append("created_at must be UTC timezone-aware")

    # If file_path exists, must match translation patterns
    if comment.file_path and not matches_translation_pattern(comment.file_path):
        errors.append(f"Comment file path not a translation file: {comment.file_path}")

    # Line number valid if file_path exists
    if comment.file_path and comment.line_number and comment.line_number <= 0:
        errors.append(f"Invalid line number: {comment.line_number}")

    return len(errors) == 0, errors
```

### Example

```python
comment = ReviewComment(
    id=1234567890,
    author="coderabbitai",
    body="nitpick: Consider using 'Hola' instead of 'Saludo' for a more natural greeting in Spanish.",
    created_at=datetime(2024, 10, 16, 8, 15, tzinfo=timezone.utc),
    file_path="src/i18n/es_ES.json",
    line_number=42,
    diff_hunk='@@ -40,7 +40,7 @@\n "welcome": "Bienvenido",\n-"greeting": "Saludo"\n+"greeting": "Hola"',
    conventional_label="nitpick",
    pull_request=pr,
    classification=None,  # Populated by classifier
    is_actionable=None
)
```

---

## Entity 5: Translation Extraction *(Added 2025-10-24)*

**Purpose**: Represents the LLM-based extraction of structured translation changes from natural language CodeRabbitAI comments.

### Fields

| Field | Type | Required | Description | Validation Rules |
|-------|------|----------|-------------|------------------|
| `comment` | `ReviewComment` | Yes | Comment being parsed | Valid ReviewComment |
| `translation_key` | `str` | Yes | Translation key being changed | Non-empty string |
| `original_value` | `str` | Yes | Current translation text | Non-empty string |
| `new_value` | `str` | Yes | Suggested replacement text | Non-empty, different from original |
| `locale` | `str` | Yes | Language locale | Format: "xx_XX" (e.g., "es_ES") |
| `reasoning` | `str` | Yes | Why the change is suggested | Non-empty string (from LLM) |
| `confidence` | `float` | Yes | LLM extraction confidence | Range: 0.0-1.0 |
| `extracted_at` | `datetime` | Yes | Extraction timestamp (UTC) | Timezone-aware datetime |
| `llm_model` | `str` | Yes | LLM model used | e.g., "claude-3-haiku-20240307" |
| `implementation_decision` | `str` | No | Auto-decision based on confidence | Enum: "implement", "human_review", "skip" |

### Relationships

- **Belongs To** `ReviewComment`: Extraction from specific comment
- **Used By** `TranslationChange`: Extraction informs translation change creation

### Confidence-Based Decision Thresholds

From research.md LLM integration section:

| Confidence Range | Decision | Description |
|------------------|----------|-------------|
| **≥ 0.80** | `implement` | High confidence, auto-implement |
| **0.60-0.79** | `human_review` | Medium confidence, flag for human review |
| **< 0.60** | `skip` | Low confidence, skip and log |

### Validation Rules

```python
def validate_translation_extraction(extraction: TranslationExtraction) -> tuple[bool, list[str]]:
    """Validate LLM extraction integrity."""
    errors = []

    # Confidence range
    if not (0.0 <= extraction.confidence <= 1.0):
        errors.append(f"Confidence must be 0.0-1.0, got {extraction.confidence}")

    # Values different
    if extraction.original_value == extraction.new_value:
        errors.append("New value must differ from original value")

    # Locale format
    if not re.match(r'^[a-z]{2}_[A-Z]{2}$', extraction.locale):
        errors.append(f"Invalid locale format: {extraction.locale} (expected: xx_XX)")

    # Translation key non-empty
    if not extraction.translation_key.strip():
        errors.append("Translation key cannot be empty")

    # Reasoning provided
    if not extraction.reasoning.strip():
        errors.append("Reasoning cannot be empty")

    # Timestamp UTC
    if extraction.extracted_at.tzinfo != timezone.utc:
        errors.append("extracted_at must be UTC timezone-aware")

    # Implementation decision consistency
    decision = should_implement_based_on_confidence(extraction.confidence)
    if extraction.implementation_decision and extraction.implementation_decision != decision:
        errors.append(f"Implementation decision '{extraction.implementation_decision}' inconsistent with confidence {extraction.confidence}")

    # Placeholder integrity
    if not validate_placeholder_integrity(extraction.original_value, extraction.new_value):
        errors.append("Placeholder variables not preserved between original and new values")

    return len(errors) == 0, errors

def should_implement_based_on_confidence(confidence: float) -> str:
    """Determine implementation decision from confidence score."""
    if confidence >= 0.80:
        return "implement"
    elif confidence >= 0.60:
        return "human_review"
    else:
        return "skip"
```

### Example

```python
extraction = TranslationExtraction(
    comment=comment,  # ReviewComment with body "nitpick: Consider using 'Hola' instead of 'Saludo'"
    translation_key="greeting",
    original_value="Saludo",
    new_value="Hola",
    locale="es_ES",
    reasoning="The suggestion recommends 'Hola' as a more natural and common Spanish greeting compared to 'Saludo', which is more formal and less frequently used in informal contexts.",
    confidence=0.87,
    extracted_at=datetime(2024, 10, 24, 14, 30, 0, tzinfo=timezone.utc),
    llm_model="claude-3-haiku-20240307",
    implementation_decision="implement"  # Auto-determined from confidence ≥ 0.80
)
```

### LLM Parsing Workflow

```
ReviewComment
    ↓
[LLM Parser Service] (services/llm_parser.py)
    ↓
TranslationExtraction
    ↓
[Confidence Threshold Check]
    ├─ ≥ 0.80 → Create TranslationChange (auto-implement)
    ├─ 0.60-0.79 → Flag for human review
    └─ < 0.60 → Skip (log low confidence)
```

---

## Entity 6: Comment Classification *(Entity numbering updated 2025-10-24)*

**Purpose**: Represents agent's analysis of a comment with classification type (Critical/Constructive/Nitpick/Question/Praise), confidence score, implementation decision, reasoning, and affected locales.

### Fields

| Field | Type | Required | Description | Validation Rules |
|-------|------|----------|-------------|------------------|
| `comment` | `ReviewComment` | Yes | Comment being classified | Valid ReviewComment |
| `type` | `str` | Yes | Classification category | Enum: "Critical", "Constructive", "Nitpick", "Question", "Praise" |
| `confidence` | `float` | Yes | Classification confidence score | Range: 0.0-1.0 |
| `implementation_decision` | `str` | Yes | Whether to implement | Enum: "implement", "skip", "clarify" |
| `reasoning` | `str` | Yes | Explanation of classification | Non-empty string |
| `affected_locales` | `list[str]` | No | Locales impacted by this comment | ISO language codes (e.g., ["es_ES", "es_MX"]) |
| `priority` | `int` | Yes | Implementation priority (1=highest) | Range: 1-3 (Critical=1, Constructive=2, Nitpick=3) |
| `requires_human_review` | `bool` | No | Whether human review needed | Default: False |
| `glossary_conflict` | `bool` | No | Whether conflicts with glossary | Default: False |

### Relationships

- **Belongs To** `ReviewComment`: Classification for specific comment
- **Influences** `TranslationChange`: Implementation depends on classification decision

### Classification Framework

From constitution translation classification framework:

| Type | Priority | Implementation | Criteria |
|------|----------|----------------|----------|
| **Critical** | 1 | MUST | Incorrect terminology, cultural issues, broken placeholders |
| **Constructive** | 2 | SHOULD | Terminology consistency, grammar, punctuation, tone |
| **Nitpick** | 3 | IMPLEMENT UNLESS SUBJECTIVE | Phrasing improvements, formatting, stylistic consistency |
| **Question** | N/A | RESPOND | Clarification requests, context queries |
| **Praise** | N/A | ACKNOWLEDGE | Positive feedback, no action |

### Validation Rules

```python
def validate_classification(classification: CommentClassification) -> tuple[bool, list[str]]:
    """Validate comment classification integrity."""
    errors = []

    # Type valid
    valid_types = ["Critical", "Constructive", "Nitpick", "Question", "Praise"]
    if classification.type not in valid_types:
        errors.append(f"Invalid classification type: {classification.type}")

    # Confidence range
    if not (0.0 <= classification.confidence <= 1.0):
        errors.append(f"Confidence must be 0.0-1.0, got {classification.confidence}")

    # Implementation decision valid
    valid_decisions = ["implement", "skip", "clarify"]
    if classification.implementation_decision not in valid_decisions:
        errors.append(f"Invalid implementation decision: {classification.implementation_decision}")

    # Priority matches type
    priority_map = {"Critical": 1, "Constructive": 2, "Nitpick": 3, "Question": 3, "Praise": 3}
    expected_priority = priority_map.get(classification.type)
    if expected_priority and classification.priority != expected_priority:
        errors.append(f"Priority {classification.priority} does not match type {classification.type}")

    # Glossary conflict only for skip decisions
    if classification.glossary_conflict and classification.implementation_decision != "skip":
        errors.append("Glossary conflicts should result in 'skip' decision")

    return len(errors) == 0, errors
```

### Example

```python
classification = CommentClassification(
    comment=comment,
    type="Nitpick",
    confidence=0.85,
    implementation_decision="implement",
    reasoning="CodeRabbitAI nitpick suggests more natural Spanish greeting. 'Hola' is more common than 'Saludo' for informal greetings. No glossary conflict detected. Implements per constitution principle IV.",
    affected_locales=["es_ES"],
    priority=3,
    requires_human_review=False,
    glossary_conflict=False
)
```

---

## Entity 7: Translation Change *(Entity numbering updated 2025-10-24)*

**Purpose**: Represents a specific translation modification with source file path, line numbers, original content, modified content, locale identifier, change type, and associated comment ID.

### Fields

| Field | Type | Required | Description | Validation Rules |
|-------|------|----------|-------------|------------------|
| `file_path` | `Path` | Yes | Translation file path | Absolute or relative path |
| `line_start` | `int` | No | Starting line number | Positive integer |
| `line_end` | `int` | No | Ending line number | >= line_start |
| `original_content` | `str` | Yes | Original translation text | Non-empty string |
| `modified_content` | `str` | Yes | Modified translation text | Non-empty, different from original |
| `locale` | `str` | Yes | Locale identifier (ISO code) | Format: "xx_XX" (e.g., "es_ES") |
| `change_type` | `str` | Yes | Type of change | Enum: "fix", "refinement", "update" |
| `comment_id` | `int` | Yes | CodeRabbitAI comment ID | Positive integer, references ReviewComment |
| `classification_type` | `str` | Yes | Classification of original comment | Enum: "Critical", "Constructive", "Nitpick" |
| `translation_key` | `str` | No | Translation key (for key-value formats) | Non-empty string for JSON/YAML |
| `validated` | `bool` | No | Whether syntax validation passed | Default: False, set True after validation |
| `validation_error` | `str` | No | Validation error message if failed | Non-empty if validated=False |

### Relationships

- **Belongs To** `ReviewComment`: Change implements specific comment
- **Belongs To** `CommitRecord`: Change included in specific commit
- **References** `TranslationPullRequest`: Change for specific PR

### Change Types

| Type | Description | Classification Source |
|------|-------------|----------------------|
| `fix` | Critical translation corrections | Critical classification |
| `refinement` | Constructive improvements | Constructive classification |
| `update` | Minor nitpick implementations | Nitpick classification |

### Validation Rules

```python
def validate_translation_change(change: TranslationChange) -> tuple[bool, list[str]]:
    """Validate translation change integrity."""
    errors = []

    # File path is translation file
    if not matches_translation_pattern(str(change.file_path)):
        errors.append(f"File path not a translation file: {change.file_path}")

    # Content different
    if change.original_content == change.modified_content:
        errors.append("Modified content must differ from original")

    # Line numbers valid
    if change.line_start and change.line_end:
        if change.line_end < change.line_start:
            errors.append(f"line_end ({change.line_end}) < line_start ({change.line_start})")

    # Locale format
    if not re.match(r'^[a-z]{2}_[A-Z]{2}$', change.locale):
        errors.append(f"Invalid locale format: {change.locale} (expected: xx_XX)")

    # Change type valid
    valid_types = ["fix", "refinement", "update"]
    if change.change_type not in valid_types:
        errors.append(f"Invalid change type: {change.change_type}")

    # Placeholder integrity
    if not validate_placeholder_integrity(change.original_content, change.modified_content):
        errors.append("Placeholder variables not preserved")

    return len(errors) == 0, errors
```

### Placeholder Integrity Check

```python
def validate_placeholder_integrity(original: str, modified: str) -> bool:
    """Ensure placeholder variables preserved."""
    original_placeholders = extract_placeholders(original)
    modified_placeholders = extract_placeholders(modified)
    return original_placeholders == modified_placeholders
```

### Example

```python
change = TranslationChange(
    file_path=Path("src/i18n/es_ES.json"),
    line_start=42,
    line_end=42,
    original_content='"greeting": "Saludo"',
    modified_content='"greeting": "Hola"',
    locale="es_ES",
    change_type="update",
    comment_id=1234567890,
    classification_type="Nitpick",
    translation_key="greeting",
    validated=True,
    validation_error=None
)
```

---

## Entity 8: Commit Record *(Entity numbering updated 2025-10-24)*

**Purpose**: Represents a git commit with commit hash, message subject, message body, timestamp, GPG signature status, verification result, and list of translation changes included.

### Fields

| Field | Type | Required | Description | Validation Rules |
|-------|------|----------|-------------|------------------|
| `commit_hash` | `str` | Yes | Git commit SHA-1 hash | 40-character hex string |
| `message_subject` | `str` | Yes | Commit message subject line | ≤50 chars (72 hard limit), capitalized, no period |
| `message_body` | `str` | Yes | Commit message body | Lines wrapped at 72 chars |
| `timestamp` | `datetime` | Yes | Commit creation time (UTC) | Timezone-aware datetime |
| `author_name` | `str` | Yes | Commit author name | Non-empty string |
| `author_email` | `str` | Yes | Commit author email | Valid email format |
| `gpg_signed` | `bool` | Yes | Whether commit is GPG signed | Must be True (constitution requirement) |
| `signature_verified` | `bool` | No | Whether GPG signature verified | True if gpg_signed=True |
| `verification_method` | `str` | No | Signature verification method | Enum: "web-flow", "gpg", None |
| `changes` | `list[TranslationChange]` | Yes | Translation changes in this commit | Non-empty list |
| `pull_request` | `TranslationPullRequest` | Yes | PR for this commit | Valid TranslationPullRequest |
| `follows_conventional_rules` | `bool` | Yes | Whether follows 7 conventional rules | Must be True (constitution requirement) |

### Relationships

- **Belongs To** `TranslationPullRequest`: Commit pushed to specific PR
- **Has Many** `TranslationChange`: Changes included in this commit

### Conventional Commit Rules

From constitution principle II (cbea.ms/git-commit):

1. Separate subject from body with blank line
2. Limit subject line to 50 characters
3. Capitalize the subject line
4. Do not end subject line with a period
5. Use imperative mood in subject line
6. Wrap body at 72 characters
7. Explain what and why vs. how

### Validation Rules

```python
def validate_commit_record(commit: CommitRecord) -> tuple[bool, list[str]]:
    """Validate commit record integrity."""
    errors = []

    # Commit hash format
    if not re.match(r'^[a-f0-9]{40}$', commit.commit_hash):
        errors.append(f"Invalid commit hash format: {commit.commit_hash}")

    # Subject length
    if len(commit.message_subject) > 72:
        errors.append(f"Subject exceeds 72 characters: {len(commit.message_subject)}")

    # Subject capitalization
    if not commit.message_subject[0].isupper():
        errors.append("Subject must start with capital letter")

    # Subject no trailing period
    if commit.message_subject.endswith("."):
        errors.append("Subject must not end with period")

    # GPG signing required
    if not commit.gpg_signed:
        errors.append("Commit must be GPG signed (constitution requirement)")

    # Signature verification if signed
    if commit.gpg_signed and not commit.signature_verified:
        errors.append("GPG signature verification failed")

    # Conventional rules compliance required
    if not commit.follows_conventional_rules:
        errors.append("Commit must follow 7 conventional rules (constitution requirement)")

    # Must include changes
    if not commit.changes:
        errors.append("Commit must include at least one translation change")

    # Timestamp UTC
    if commit.timestamp.tzinfo != timezone.utc:
        errors.append("Timestamp must be UTC timezone-aware")

    return len(errors) == 0, errors
```

### Example

```python
commit = CommitRecord(
    commit_hash="a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0",
    message_subject="Update Spanish translation: greeting formality",
    message_body="""What: Changed 'Saludo' to 'Hola' for more natural greeting
Why: CodeRabbitAI nitpick for localization consistency with
     informal Spanish usage patterns
CodeRabbitAI-Comment-ID: 1234567890
Locale: es_ES""",
    timestamp=datetime(2024, 10, 16, 14, 30, tzinfo=timezone.utc),
    author_name="PR Guardian Bot",
    author_email="pr-guardian@example.com",
    gpg_signed=True,
    signature_verified=True,
    verification_method="web-flow",
    changes=[change],  # TranslationChange objects
    pull_request=pr,
    follows_conventional_rules=True
)
```

---

## Entity 9: Session Report *(Entity numbering updated 2025-10-24)*

**Purpose**: Represents execution session results with session start/end times, repositories processed, PRs discovered and processed, total comments by classification, changes implemented, commits created, issues filed, and errors encountered.

### Fields

| Field | Type | Required | Description | Validation Rules |
|-------|------|----------|-------------|------------------|
| `session_id` | `str` | Yes | Unique session identifier | Format: "session_YYYYMMDD_HHMMSS_<uuid>" |
| `start_time` | `datetime` | Yes | Session start timestamp (UTC) | Timezone-aware datetime |
| `end_time` | `datetime` | No | Session end timestamp (UTC) | Timezone-aware datetime, > start_time |
| `repositories_processed` | `list[str]` | Yes | Repository identifiers processed | Format: ["owner/repo"] |
| `prs_discovered` | `int` | Yes | Total PRs discovered | Non-negative integer |
| `prs_processed` | `int` | Yes | PRs successfully processed | ≤ prs_discovered |
| `prs_skipped` | `int` | Yes | PRs skipped (state/author mismatch) | ≥ 0 |
| `prs_failed` | `int` | Yes | PRs failed during processing | ≥ 0 |
| `comments_total` | `int` | Yes | Total comments retrieved | Non-negative integer |
| `comments_by_classification` | `dict[str, int]` | Yes | Comment counts by type | Keys: "Critical", "Constructive", "Nitpick", "Question", "Praise" |
| `changes_implemented` | `int` | Yes | Translation changes implemented | Non-negative integer |
| `commits_created` | `int` | Yes | Commits created and pushed | Non-negative integer |
| `feedback_issues_created` | `int` | Yes | Feedback issues filed | Non-negative integer |
| `errors_encountered` | `list[str]` | Yes | Error messages during execution | Empty list if no errors |
| `duration_seconds` | `float` | No | Execution duration in seconds | Calculated: end_time - start_time |
| `success` | `bool` | Yes | Overall session success status | True if no critical errors |

### Relationships

- **References** `PRGuardianConfiguration`: Session executed with specific config
- **Has Many** `TranslationPullRequest`: PRs processed in this session
- **Has Many** `CommitRecord`: Commits created in this session
- **Has Many** `FeedbackIssue`: Issues created in this session

### Session Success Criteria

```python
def calculate_session_success(report: SessionReport) -> bool:
    """Determine if session was successful."""
    # No critical errors
    if any("CRITICAL" in error or "FATAL" in error for error in report.errors_encountered):
        return False

    # At least some PRs processed if discovered
    if report.prs_discovered > 0 and report.prs_processed == 0:
        return False

    # Commits created if changes implemented
    if report.changes_implemented > 0 and report.commits_created == 0:
        return False

    # No complete execution failures
    if report.prs_failed == report.prs_discovered and report.prs_discovered > 0:
        return False

    return True
```

### Validation Rules

```python
def validate_session_report(report: SessionReport) -> tuple[bool, list[str]]:
    """Validate session report data integrity."""
    errors = []

    # Timestamps valid
    if report.start_time.tzinfo != timezone.utc:
        errors.append("start_time must be UTC timezone-aware")
    if report.end_time and report.end_time.tzinfo != timezone.utc:
        errors.append("end_time must be UTC timezone-aware")
    if report.end_time and report.end_time <= report.start_time:
        errors.append("end_time must be after start_time")

    # PR counts consistent
    total_prs = report.prs_processed + report.prs_skipped + report.prs_failed
    if total_prs != report.prs_discovered:
        errors.append(f"PR counts inconsistent: {total_prs} != {report.prs_discovered}")

    # Classification counts sum to total
    classification_sum = sum(report.comments_by_classification.values())
    if classification_sum != report.comments_total:
        errors.append(f"Classification counts ({classification_sum}) != total comments ({report.comments_total})")

    # Required classification keys
    required_keys = ["Critical", "Constructive", "Nitpick", "Question", "Praise"]
    for key in required_keys:
        if key not in report.comments_by_classification:
            errors.append(f"Missing classification key: {key}")

    # Changes and commits correlation
    if report.changes_implemented > 0 and report.commits_created == 0:
        errors.append("Changes implemented but no commits created")

    return len(errors) == 0, errors
```

### Example

```python
report = SessionReport(
    session_id="session_20241016_023000_a1b2c3d4",
    start_time=datetime(2024, 10, 16, 2, 30, 0, tzinfo=timezone.utc),
    end_time=datetime(2024, 10, 16, 2, 38, 45, tzinfo=timezone.utc),
    repositories_processed=["bisq-network/bisq-mobile", "bisq-network/bisq2"],
    prs_discovered=3,
    prs_processed=2,
    prs_skipped=1,  # One PR already merged
    prs_failed=0,
    comments_total=18,
    comments_by_classification={
        "Critical": 2,
        "Constructive": 5,
        "Nitpick": 8,
        "Question": 2,
        "Praise": 1
    },
    changes_implemented=15,  # Critical + Constructive + most Nitpicks
    commits_created=15,       # Atomic commits per change
    feedback_issues_created=1,
    errors_encountered=[],
    duration_seconds=525.0,  # ~8.75 minutes
    success=True
)
```

---

## Entity 10: Feedback Pattern *(Entity numbering updated 2025-10-24)*

**Purpose**: Represents aggregated insights from a session with pattern type, frequency count, affected locales, specific examples, and improvement recommendations.

### Fields

| Field | Type | Required | Description | Validation Rules |
|-------|------|----------|-------------|------------------|
| `pattern_type` | `str` | Yes | Type of feedback pattern | Enum: "terminology", "punctuation", "formality", "grammar", "placeholder", "cultural" |
| `frequency` | `int` | Yes | Number of occurrences in session | Positive integer |
| `affected_locales` | `list[str]` | Yes | Locales where pattern appears | ISO language codes |
| `examples` | `list[str]` | Yes | Specific example comments | Non-empty list, 1-5 examples |
| `severity` | `str` | Yes | Pattern severity level | Enum: "critical", "moderate", "minor" |
| `recommendation` | `str` | Yes | Suggested improvement action | Non-empty string |
| `session` | `SessionReport` | Yes | Session where pattern identified | Valid SessionReport |
| `automated_fix_possible` | `bool` | No | Whether can be automated | Default: False |

### Relationships

- **Belongs To** `SessionReport`: Pattern identified in specific session
- **Influences** `FeedbackIssue`: Patterns aggregated into feedback issues

### Pattern Types

| Type | Description | Example |
|------|-------------|---------|
| `terminology` | Inconsistent term usage | "Login" vs "Sign In" across locales |
| `punctuation` | Punctuation inconsistencies | Missing periods, incorrect quote styles |
| `formality` | Tone mismatches | Informal "you" vs formal "您" in Chinese |
| `grammar` | Grammatical errors | Gender agreement, verb conjugation |
| `placeholder` | Placeholder variable issues | Incorrect {variable} syntax |
| `cultural` | Cultural appropriateness | Colors, metaphors, idioms |

### Validation Rules

```python
def validate_feedback_pattern(pattern: FeedbackPattern) -> tuple[bool, list[str]]:
    """Validate feedback pattern data."""
    errors = []

    # Pattern type valid
    valid_types = ["terminology", "punctuation", "formality", "grammar", "placeholder", "cultural"]
    if pattern.pattern_type not in valid_types:
        errors.append(f"Invalid pattern type: {pattern.pattern_type}")

    # Frequency positive
    if pattern.frequency <= 0:
        errors.append(f"Frequency must be positive: {pattern.frequency}")

    # Locales non-empty
    if not pattern.affected_locales:
        errors.append("Must specify at least one affected locale")

    # Examples provided
    if not (1 <= len(pattern.examples) <= 5):
        errors.append(f"Must provide 1-5 examples, got {len(pattern.examples)}")

    # Severity valid
    if pattern.severity not in ["critical", "moderate", "minor"]:
        errors.append(f"Invalid severity: {pattern.severity}")

    # Recommendation non-empty
    if not pattern.recommendation.strip():
        errors.append("Recommendation cannot be empty")

    return len(errors) == 0, errors
```

### Example

```python
pattern = FeedbackPattern(
    pattern_type="terminology",
    frequency=8,
    affected_locales=["es_ES", "es_MX", "es_AR"],
    examples=[
        "Inconsistent 'Login' vs 'Iniciar sesión' across Spanish locales",
        "'Sign in' translated as 'Registrarse' (should be 'Iniciar sesión')",
        "Mixed usage of 'Usuario' and 'Cuenta' for 'User'"
    ],
    severity="moderate",
    recommendation="Update translation glossary to standardize 'Login' → 'Iniciar sesión' across all Spanish locales. Add glossary validation to translation automation pipeline.",
    session=report,
    automated_fix_possible=True
)
```

---

## Entity 11: Feedback Issue *(Entity numbering updated 2025-10-24)*

**Purpose**: Represents created GitHub issue with issue number, title, body content, creation timestamp, target repository, and associated session report.

### Fields

| Field | Type | Required | Description | Validation Rules |
|-------|------|----------|-------------|------------------|
| `issue_number` | `int` | Yes | GitHub issue number | Positive integer |
| `title` | `str` | Yes | Issue title | Non-empty, ≤100 chars |
| `body` | `str` | Yes | Issue body (markdown) | Non-empty, structured format |
| `created_at` | `datetime` | Yes | Issue creation timestamp (UTC) | Timezone-aware datetime |
| `repository` | `str` | Yes | Feedback repository identifier | Format: "owner/repository" |
| `url` | `str` | Yes | GitHub issue URL | Valid GitHub issue URL |
| `session` | `SessionReport` | Yes | Session that created this issue | Valid SessionReport |
| `patterns` | `list[FeedbackPattern]` | Yes | Patterns included in issue | Non-empty list |
| `labels` | `list[str]` | No | GitHub issue labels | e.g., ["translation-feedback", "automated"] |

### Relationships

- **Belongs To** `SessionReport`: Issue created from specific session
- **Has Many** `FeedbackPattern`: Patterns aggregated in this issue
- **References** `PRGuardianConfiguration`: Issue created in configured feedback repository

### Issue Body Structure

```markdown
# Translation Feedback - Session {session_id}

**Session Date**: {date}
**Repositories Processed**: {list}
**PRs Analyzed**: {count}
**Comments Reviewed**: {count}

## Summary

{High-level overview of patterns identified}

## Patterns Identified

### Pattern 1: {pattern_type} ({severity})
- **Frequency**: {count} occurrences
- **Affected Locales**: {list}
- **Examples**:
  - {example 1}
  - {example 2}
- **Recommendation**: {action}

[Repeat for each pattern]

## Recommendations for Translation System

1. {Prioritized action item 1}
2. {Prioritized action item 2}

## Session Statistics

- Total Comments: {count}
- Critical Issues: {count}
- Constructive Suggestions: {count}
- Nitpicks: {count}
- Changes Implemented: {count}
- Commits Created: {count}

---

🤖 Generated by PR Guardian | Session: {session_id}
```

### Validation Rules

```python
def validate_feedback_issue(issue: FeedbackIssue) -> tuple[bool, list[str]]:
    """Validate feedback issue data."""
    errors = []

    # Issue number positive
    if issue.issue_number <= 0:
        errors.append(f"Invalid issue number: {issue.issue_number}")

    # Title length
    if len(issue.title) > 100:
        errors.append(f"Title exceeds 100 characters: {len(issue.title)}")

    # Repository format
    if not re.match(r'^[a-zA-Z0-9-]+/[a-zA-Z0-9._-]+$', issue.repository):
        errors.append(f"Invalid repository format: {issue.repository}")

    # URL valid
    if not issue.url.startswith("https://github.com/"):
        errors.append(f"Invalid GitHub issue URL: {issue.url}")

    # Timestamp UTC
    if issue.created_at.tzinfo != timezone.utc:
        errors.append("created_at must be UTC timezone-aware")

    # Patterns non-empty
    if not issue.patterns:
        errors.append("Feedback issue must include at least one pattern")

    return len(errors) == 0, errors
```

### Example

```python
issue = FeedbackIssue(
    issue_number=456,
    title="Translation Feedback - Session 20241016",
    body="""# Translation Feedback - Session session_20241016_023000_a1b2c3d4

**Session Date**: 2024-10-16
**Repositories Processed**: bisq-network/bisq-mobile, bisq-network/bisq2
**PRs Analyzed**: 2
**Comments Reviewed**: 18

## Summary

Identified 3 recurring terminology inconsistencies across Spanish locales and 2 punctuation patterns affecting German translations.

## Patterns Identified

### Pattern 1: terminology (moderate)
- **Frequency**: 8 occurrences
- **Affected Locales**: es_ES, es_MX, es_AR
- **Examples**:
  - Inconsistent 'Login' vs 'Iniciar sesión' across Spanish locales
  - 'Sign in' translated as 'Registrarse' (should be 'Iniciar sesión')
- **Recommendation**: Update translation glossary to standardize 'Login' → 'Iniciar sesión'

[Additional patterns...]

## Recommendations for Translation System

1. Add glossary validation to translation automation pipeline
2. Implement terminology consistency checker for Spanish locales

## Session Statistics

- Total Comments: 18
- Critical Issues: 2
- Constructive Suggestions: 5
- Nitpicks: 8
- Changes Implemented: 15
- Commits Created: 15

---

🤖 Generated by PR Guardian | Session: session_20241016_023000_a1b2c3d4""",
    created_at=datetime(2024, 10, 16, 2, 40, 0, tzinfo=timezone.utc),
    repository="bisq-network/translation-automation",
    url="https://github.com/bisq-network/translation-automation/issues/456",
    session=report,
    patterns=[pattern],  # FeedbackPattern objects
    labels=["translation-feedback", "automated", "pr-guardian"]
)
```

---

## Entity Relationship Diagram *(Updated 2025-10-24 with LLM Integration)*

```
PRGuardianConfiguration
    ├─── 1:N ─── RepositoryTarget
    │                 ├─── 1:N ─── TranslationPullRequest
    │                                  ├─── 1:N ─── ReviewComment
    │                                  │               ├─── 1:1 ─── TranslationExtraction (NEW)
    │                                  │               │               └─── used by ─── TranslationChange
    │                                  │               ├─── 1:1 ─── CommentClassification
    │                                  │               └─── 1:N ─── TranslationChange
    │                                  └─── 1:N ─── CommitRecord
    │                                                      └─── N:N ─── TranslationChange
    └─── 1:1 ─── FeedbackRepository

SessionReport
    ├─── N:N ─── TranslationPullRequest
    ├─── N:N ─── CommitRecord
    ├─── 1:N ─── FeedbackPattern
    └─── 1:N ─── FeedbackIssue
                     └─── N:N ─── FeedbackPattern
```

**Key Change**: TranslationExtraction (Entity 5) represents LLM-based parsing of ReviewComment natural language into structured translation change data. This extraction informs the creation of TranslationChange entities.

## State Machines

### Pull Request Processing State Machine

```
[Discovered] ─(matches criteria)→ [Eligible]
                                        │
                         (start processing)
                                        ↓
                                  [Processing]
                                        │
                    ┌───────────────────┼───────────────────┐
          (all changes applied)  (partial success)  (error occurred)
                    │                   │                   │
                    ↓                   ↓                   ↓
              [Completed]      [Partially Completed]   [Failed]
```

### Comment Classification Flow

```
[Retrieved] ─(analyze)→ [Classified]
                             │
              ┌──────────────┼──────────────┐
     (implement)    (skip)           (clarify)
              │              │                │
              ↓              ↓                ↓
      [Implementing]   [Skipped]      [Needs Review]
              │              │                │
     (validation OK) (log reasoning)  (human review)
              │              │                │
              ↓              ↓                ↓
        [Committed]    [Acknowledged]  [Pending Clarification]
```

## Summary

This data model defines 11 core entities with comprehensive field definitions, validation rules, relationships, and state transitions. All entities enforce constitution requirements including UTC timestamps, GPG signing, conventional commits, and translation-only scope. The model supports the complete PR Guardian workflow from configuration through execution to feedback aggregation.

**Key Update (2025-10-24)**: Added Entity 5 (TranslationExtraction) to support LLM-based comment parsing with Anthropic Claude 3 Haiku. This entity enables natural language understanding of CodeRabbitAI comments with confidence-based implementation decisions (≥0.80 auto-implement, 0.60-0.79 human review, <0.60 skip).

**Entity List**:
1. PR Guardian Configuration
2. Repository Target
3. Translation Pull Request
4. Review Comment
5. **Translation Extraction** *(NEW - LLM parsing)*
6. Comment Classification
7. Translation Change
8. Commit Record
9. Session Report
10. Feedback Pattern
11. Feedback Issue

**Next Steps**: Create contracts/llm-api.md for Anthropic API integration and update quickstart.md with LLM setup instructions to complete Phase 1.
