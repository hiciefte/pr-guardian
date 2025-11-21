# Implementation Plan: PR Guardian - Autonomous Translation Review Agent

**Branch**: `001-pr-guardian-agent` | **Date**: 2025-10-24 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-pr-guardian-agent/spec.md`

## Summary

PR Guardian is an autonomous agent that monitors GitHub repositories for translation PRs, automatically implements CodeRabbitAI review comments and nitpicks, creates GPG-signed commits following conventional standards, and provides feedback to improve the translation automation system. The agent runs on a scheduled basis in a Docker container for security isolation, using GitHub CLI for API interactions, SSH deploy keys for repository access, and a GPG bot key for commit signing.

**Core Capabilities**:
- Scheduled PR discovery and comment retrieval from configured repositories
- Comment classification per translation constitution framework
- Automated translation file modification with syntax validation
- GPG-signed commit creation following 7 conventional commit rules
- Multi-repository support with independent processing contexts
- Session feedback aggregation and issue creation for translation system improvements
- Comprehensive error handling with rollback and retry logic

## Technical Context

**Language/Version**: Python 3.11+ (async/await support, modern type hints, security updates)
**Primary Dependencies**:
- GitHub CLI (gh) for GitHub API interactions
- GitPython for local git operations and commit management
- PyYAML, python-dotenv for configuration handling
- Schedule library for cron-style execution management
- Click for CLI interface
- anthropic==0.40.0 for LLM-based comment parsing (Claude 3 Haiku)
- pydantic==2.10.0 for structured output schemas and validation
- tenacity==9.0.0 for retry logic with exponential backoff
- redis==5.2.0 (optional) for semantic caching of LLM responses

**Storage**: File-based (configuration files, session logs, validation reports saved to disk)
**Testing**: pytest with pytest-asyncio, pytest-mock for unit and integration tests
**Target Platform**: Docker container (Alpine Linux base for minimal footprint)
**Project Type**: Single CLI application with modular service architecture
**Performance Goals**:
- Process PRs with up to 20 comments in under 5 minutes (including LLM parsing latency: ~1.4s per comment, parallelized to 10 concurrent)
- Handle up to 3 repositories per execution within 30-minute window
- Maintain 99% scheduled execution reliability
- LLM parsing: Sequential 200 comments in ~5min, parallel (10 concurrent) in ~30s
- Achieve 85-90% accuracy in natural language comment parsing with confidence thresholds

**Constraints**:
- Translation files only (*.properties, **/i18n/**/*.json, **/locales/**/*.yml, **/lang/**/*)
- GPG-signed commits mandatory (non-negotiable per constitution)
- Conventional commit format required (7 rules, non-negotiable per constitution)
- 30-minute maximum execution window to prevent blocking subsequent runs
- GitHub API rate limit compliance (exponential backoff required)

**Scale/Scope**:
- Up to 10 monitored repositories per agent instance
- Up to 50 comments processed per PR (configurable limit)
- Session reports and validation logs retained for 30 days
- Support for 8+ language locale variants per translation file
- LLM operational cost: $1.13-2.40/month for 6,000 requests (optimized with prompt caching and semantic caching)

**Deployment Architecture**:
- Docker container with isolated runtime environment
- Secrets directory mounted as volume: `/secrets/deploy_key` (SSH), `/secrets/gpg_bot_key` (GPG private key)
- GitHub CLI configured with authentication
- Environment variables: `ANTHROPIC_API_KEY` (required), `LLM_MODEL`, `LLM_MAX_TOKENS`, `LLM_CONFIDENCE_THRESHOLD`
- Optional Redis container for semantic caching (redis:7-alpine) with 7-day TTL
- Cron or external scheduler triggers container execution
- Logs output to stdout/stderr for container orchestration logging

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### ✅ Translation Quality First (Principle I)
- **Compliance**: Agent implements comment classification framework distinguishing Critical, Constructive, Nitpick, Question, Praise categories
- **Implementation**: Classification logic in `services/comment_classifier.py` evaluates each comment against translation-specific criteria
- **Validation**: Translation file parsers validate syntax and placeholder integrity before/after changes

### ✅ Conventional Commit Standards (Principle II)
- **Compliance**: All commits follow 7 rules via commit message builder
- **Implementation**: `services/commit_builder.py` enforces subject/body separation, 50-char limit, capitalization, no period, imperative mood, 72-char body wrap, explain why/what
- **Validation**: GPG signing mandatory via `git commit -S`, signature verification via `git verify-commit` before push

### ✅ Translation-Only Scope (Principle III)
- **Compliance**: File path filters restrict operations to translation file patterns
- **Implementation**: `services/file_validator.py` checks paths against whitelist before modification
- **Rejection**: Any non-translation file modification attempts logged and skipped

### ✅ Nitpick Implementation for Translations (Principle IV)
- **Compliance**: Translation nitpicks classified as "Constructive Suggestions" and implemented by default
- **Implementation**: Classification logic treats nitpicks differently than code review patterns
- **Exception Handling**: Subjective or glossary-contradicting nitpicks logged and acknowledged without implementation

### ✅ Incremental and Reversible Changes (Principle V)
- **Compliance**: Atomic commits with rollback capability
- **Implementation**: Each translation change committed independently with reference to review comment ID
- **Error Recovery**: Failed implementations trigger `git reset --hard` rollback and error logging

### Constitution Gate Status: ✅ PASS
All core principles satisfied. No complexity violations requiring justification.

## Project Structure

### Documentation (this feature)

```text
specs/001-pr-guardian-agent/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   ├── github-api.md    # GitHub REST API interaction patterns
│   └── llm-api.md       # Anthropic API interaction patterns (Added 2025-10-24)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── models/
│   ├── config.py           # PR Guardian configuration model
│   ├── repository.py       # Repository target model
│   ├── pull_request.py     # Translation PR model
│   ├── comment.py          # Review comment model
│   ├── classification.py   # Comment classification result
│   ├── translation.py      # Translation change model
│   ├── commit.py           # Commit record model
│   └── session.py          # Session report model
│
├── services/
│   ├── config_loader.py    # Configuration loading and validation
│   ├── github_client.py    # GitHub CLI wrapper for API interactions
│   ├── pr_discovery.py     # PR discovery and filtering service
│   ├── comment_retrieval.py # Comment fetching from GitHub API
│   ├── comment_classifier.py # Translation comment classification
│   ├── llm_parser.py       # LLM-based comment parsing with Claude 3 Haiku
│   ├── file_validator.py   # Translation file path and syntax validation
│   ├── translation_processor.py # Apply translation changes to files
│   ├── commit_builder.py   # Conventional commit message generator
│   ├── gpg_signer.py       # GPG commit signing and verification
│   ├── git_operations.py   # Git operations (checkout, commit, push)
│   ├── feedback_aggregator.py # Session feedback pattern analysis
│   ├── issue_creator.py    # GitHub issue creation for feedback
│   └── session_manager.py  # Execution session orchestration
│
├── cli/
│   ├── main.py             # CLI entry point with Click
│   ├── run.py              # Execute agent run command
│   ├── config.py           # Configuration management commands
│   └── validate.py         # Validation and testing commands
│
└── lib/
    ├── parsers/
    │   ├── properties.py   # Java properties file parser
    │   ├── json_parser.py  # JSON translation file parser
    │   └── yaml_parser.py  # YAML translation file parser
    ├── validators/
    │   ├── placeholder.py  # Placeholder variable validation
    │   └── syntax.py       # Translation file syntax validation
    └── utils/
        ├── logging.py      # Structured logging configuration
        ├── retry.py        # Exponential backoff retry logic
        └── timing.py       # UTC timestamp and duration utilities

tests/
├── contract/
│   ├── test_github_api.py  # GitHub REST API contract tests
│   └── test_git_cli.py     # Git command contract tests
│
├── integration/
│   ├── test_pr_workflow.py # End-to-end PR processing workflow
│   ├── test_multi_repo.py  # Multi-repository processing
│   └── test_feedback_loop.py # Feedback issue creation
│
└── unit/
    ├── models/             # Model validation tests
    ├── services/           # Service logic tests
    └── lib/                # Library utility tests

docker/
├── Dockerfile              # Multi-stage build with Python 3.11 Alpine
├── entrypoint.sh           # Container startup script
└── docker-compose.yml      # Local development orchestration

config/
├── config.example.yml      # Example configuration template
└── .env.example            # Example environment variables

secrets/                    # Mounted volume in Docker (NOT in git)
├── deploy_key              # SSH private key for repository access
├── deploy_key.pub          # SSH public key
└── gpg_bot_key             # GPG private key for commit signing
```

**Structure Decision**: Single project structure selected as appropriate for this CLI autonomous agent. The application is a standalone service without frontend/backend separation. Modular service architecture with clear separation of concerns: models for data structures, services for business logic, CLI for interface, lib for utilities. Docker containerization provides deployment isolation and security.

## Complexity Tracking

No constitution violations detected. All principles satisfied without complexity justification required.

## Phase 0: Research & Technology Decisions

**Status**: To be completed by `/speckit.plan` command

Research tasks to be executed:

1. **GitHub CLI Best Practices for Programmatic Use**
   - Authentication patterns for automated scripts
   - Rate limit handling and exponential backoff strategies
   - Error codes and retry scenarios
   - JSON output parsing and error detection

2. **GPG Signing in Docker Containers**
   - GPG key import and configuration in containerized environment
   - Passphrase-less key generation for automated signing
   - Git configuration for signed commits
   - Signature verification workflow

3. **SSH Deploy Key Management**
   - SSH agent configuration in Docker
   - Deploy key permissions and scope
   - Known hosts management for GitHub
   - Key rotation and expiration handling

4. **Translation File Parsing Libraries**
   - Python libraries for .properties, JSON, YAML parsing
   - Syntax validation approaches
   - Placeholder variable regex patterns
   - Character encoding handling (UTF-8, etc.)

5. **Cron Scheduling in Docker**
   - Container restart vs persistent cron
   - Execution logging and output capture
   - Time zone handling (UTC enforcement)
   - Health check and monitoring integration

6. **Conventional Commit Message Generation**
   - Automated commit message formatting
   - Body wrap algorithms (72 characters)
   - Imperative mood detection/generation
   - Subject line truncation strategies

7. **LLM Integration for Comment Parsing** *(Added 2025-10-24)*
   - Natural language comment parsing to extract structured translation changes
   - LLM provider selection (Anthropic Claude 3 Haiku vs GPT-4o-mini vs local models)
   - Cost optimization strategies (prompt caching, semantic caching)
   - Reliability patterns (retry logic, circuit breakers, confidence thresholds)
   - Parallel processing for performance within 30-minute execution window
   - Pydantic schemas for structured output validation

**Output**: `research.md` will document decisions, rationale, alternatives considered, and selected approaches for each research area.

## Phase 1: Design & Contracts

**Status**: To be completed by `/speckit.plan` command

### Design Artifacts to Generate

1. **Data Model** (`data-model.md`):
   - Extract 10 key entities from spec (PR Guardian Configuration, Repository Target, Translation Pull Request, Review Comment, Comment Classification, Translation Change, Commit Record, Session Report, Feedback Pattern, Feedback Issue)
   - Define fields, relationships, validation rules
   - Document state transitions (e.g., PR states, comment classification flow)

2. **API Contracts** (`contracts/github-api.md`, `contracts/llm-api.md`):
   - **GitHub API**: REST API interaction patterns, endpoint specifications for PR discovery, comment retrieval, issue creation
   - **LLM API**: Anthropic API interaction patterns for comment parsing, tool use/function calling schemas, prompt caching strategies
   - Request/response schemas for both APIs
   - Error handling and retry logic with exponential backoff
   - Rate limit compliance patterns

3. **Quickstart Guide** (`quickstart.md`):
   - Docker build and run instructions
   - Secret configuration (deploy_key, gpg_bot_key, ANTHROPIC_API_KEY)
   - Configuration file setup with LLM parameters
   - Optional Redis deployment for semantic caching
   - First execution walkthrough
   - Cost monitoring and optimization guidance
   - Troubleshooting common issues (including LLM-specific errors)

### Agent Context Update

After Phase 1 completion, the agent-specific context file will be updated with technology choices:
- Python 3.11+
- GitHub CLI
- GitPython
- Docker (Alpine Linux)
- Translation file parsers (properties, JSON, YAML)
- Anthropic Claude 3 Haiku for LLM comment parsing
- Pydantic for structured output schemas
- Redis (optional) for semantic caching
- pytest testing framework

**Output**: `data-model.md`, `contracts/github-api.md`, `contracts/llm-api.md`, `quickstart.md`, and updated agent context file.

## Implementation Phases (Post-Planning)

*Note: These phases are executed by `/speckit.tasks` and `/speckit.implement` commands, not by `/speckit.plan`.*

### Phase 2: Task Generation (via `/speckit.tasks`)
- Generate dependency-ordered implementation tasks from this plan
- Map tasks to spec requirements and design artifacts
- Establish task dependencies and execution order
- Create tasks.md with actionable implementation steps

### Phase 3: Implementation (via `/speckit.implement`)
- Execute tasks.md in dependency order
- Implement models, services, CLI, tests
- Build Docker container
- Configure secrets and deployment
- Validate against constitution principles
- Run integration tests

## Post-Design Constitution Validation

*GATE: Re-check after Phase 1 design artifacts completed.*
*Date*: 2025-10-24
*Phase*: 1 (Design) Complete - All artifacts generated

### ✅ Translation Quality First (Principle I) - VALIDATED

**Pre-Implementation Compliance**:
- ✅ **Comment Classification Framework**: `CommentClassification` entity (data-model.md) implements 5-category framework with confidence scoring
- ✅ **Translation-Specific Criteria**: Classification types distinguish Critical (broken functionality), Constructive (quality improvements), Nitpick (minor improvements), Question (clarification), Praise (acknowledgment)
- ✅ **Syntax Validation**: `TranslationChange` entity includes `validated` boolean and `validation_error` fields for pre-commit syntax validation
- ✅ **Placeholder Integrity**: `validate_placeholder_integrity()` function (data-model.md) ensures placeholder variables preserved across changes
- ✅ **Cross-Locale Consistency**: `affected_locales` field in classification tracks impact across language variants

**Research Validation**:
- ✅ **Translation File Parsers** (research.md): javaproperties (0.8.2+), json+jsonschema (4.25.1+), PyYAML (6.0+) selected for format-specific validation
- ✅ **Encoding Detection**: charset-normalizer (3.4.1+) prevents UTF-8/Latin-1 corruption issues
- ✅ **Placeholder Patterns**: Regex validation for `{variable}`, `%s`, `{{key}}`, `$variable`, `%(name)s` formats

**Design Enforcement**:
- ✅ **File Validator Service**: `services/file_validator.py` restricts operations to translation patterns only
- ✅ **Validation Gates**: Pre-implementation validation (constitution check) and post-implementation verification (quality gates)
- ✅ **Error Recovery**: `TranslationChange.validation_error` field captures syntax failures for rollback

**Conclusion**: Principle I fully satisfied with comprehensive validation, classification, and quality assurance mechanisms.

---

### ✅ Conventional Commit Standards (Principle II) - VALIDATED

**Pre-Implementation Compliance**:
- ✅ **7 Rules Enforcement**: `CommitRecord` entity (data-model.md) includes `follows_conventional_rules` boolean (MUST be True)
- ✅ **Commit Message Builder**: Template-based generation (research.md) algorithmically enforces all 7 rules
- ✅ **GPG Signing Mandatory**: `CommitRecord.gpg_signed` MUST be True (constitution requirement), validation rejects unsigned commits
- ✅ **Signature Verification**: `signature_verified` boolean ensures commits verified before push via `git verify-commit`
- ✅ **Imperative Mood**: `ensure_imperative_mood()` function converts past-tense verbs to imperative
- ✅ **Subject/Body Formatting**: Template system enforces 50-char subject limit, 72-char body wrap, capitalization, no period

**Research Validation**:
- ✅ **GitHub Web-Flow Signing** (research.md): Recommended approach eliminates GPG key management complexity, provides automatic GitHub verification
- ✅ **Traditional GPG Alternative**: Documented for systems requiring email-based verification with passphrase-less keys
- ✅ **Commit Message Generation**: `CommitMessageTemplate` class implements all 7 rules with validation function

**Design Enforcement**:
- ✅ **Commit Builder Service**: `services/commit_builder.py` generates compliant messages with CodeRabbitAI comment references
- ✅ **Validation Function**: `validate_commit_message()` checks all 7 rules before commit creation
- ✅ **Atomic Commits**: `CommitRecord` entity tracks individual changes, enabling one commit per logical change

**API Contract Validation**:
- ✅ **Web-Flow Signing** (contracts/github-api.md): `gh api repos/owner/repo/git/commits` creates signed commits via GitHub API
- ✅ **Signature Verification**: `gh api repos/owner/repo/commits/{sha}` retrieves verification status (`verified: true`)
- ✅ **Commit Structure**: API contract defines message format with what/why body structure

**Conclusion**: Principle II fully satisfied with mandatory GPG signing, comprehensive rule enforcement, and algorithmic validation.

---

### ✅ Translation-Only Scope (Principle III) - VALIDATED

**Pre-Implementation Compliance**:
- ✅ **File Pattern Restrictions**: `RepositoryTarget` entity (data-model.md) includes `translation_file_patterns` with default patterns
- ✅ **Default Patterns**: `*.properties`, `**/i18n/**/*.json`, `**/locales/**/*.yml`, `**/lang/**/*` (constitution-compliant)
- ✅ **Validation Rules**: `matches_translation_pattern()` function filters non-translation files
- ✅ **Path Filtering**: `TranslationPullRequest.translation_files` only includes files matching patterns
- ✅ **Rejection Logging**: Any non-translation file modification attempts logged and skipped

**Research Validation**:
- ✅ **Translation File Parsers** (research.md): Format-specific parsers (properties, JSON, YAML) ensure only translation files processed
- ✅ **Syntax Validation**: Each parser includes validation to detect non-translation files
- ✅ **Encoding Handling**: charset-normalizer detects encoding for translation-specific character sets

**Design Enforcement**:
- ✅ **File Validator Service**: `services/file_validator.py` checks paths before modification
- ✅ **PR File Filtering**: `filter_translation_files()` function (github-api.md) applies patterns to PR file list
- ✅ **Change Validation**: `validate_translation_change()` rejects changes to non-matching paths

**API Contract Validation**:
- ✅ **PR File Retrieval** (contracts/github-api.md): `gh pr view --json files` retrieves all PR files
- ✅ **Pattern Matching**: `filter_translation_files()` uses fnmatch against configured patterns
- ✅ **Translation-Only Processing**: Only matching files passed to translation processors

**Conclusion**: Principle III fully satisfied with strict file pattern enforcement, pre-processing validation, and automatic rejection of non-translation modifications.

---

### ✅ Nitpick Implementation for Translations (Principle IV) - VALIDATED

**Pre-Implementation Compliance**:
- ✅ **Nitpick Classification**: `CommentClassification` entity distinguishes "Nitpick" as separate type with priority 3
- ✅ **Default Implementation**: `implementation_decision` enum includes "implement" as default for nitpicks
- ✅ **Exception Handling**: `glossary_conflict` boolean captures subjective/contradicting nitpicks for skip decision
- ✅ **Reasoning Field**: `classification.reasoning` documents why nitpicks implemented or skipped
- ✅ **Translation-Specific Framework**: Classification criteria recognize nitpicks often contain legitimate translation improvements

**Research Validation**:
- ✅ **Comment Classification**: Constitution principle IV (research.md) defines translation nitpicks as "Implement Unless Subjective"
- ✅ **Examples**: "Minor phrasing improvements", "Formatting preferences", "Stylistic consistency" treated as constructive

**Design Enforcement**:
- ✅ **Classifier Service**: `services/comment_classifier.py` evaluates nitpicks differently than code review patterns
- ✅ **Priority System**: Nitpicks assigned priority 3 (after Critical=1, Constructive=2) for implementation order
- ✅ **Skip Logic**: Glossary conflicts trigger skip decision with reasoning logged

**API Contract Validation**:
- ✅ **Conventional Labels** (contracts/github-api.md): `ReviewComment.conventional_label` captures CodeRabbitAI's "nitpick" label
- ✅ **Classification Mapping**: Nitpicks classified as "Translation Nitpick" category with default implement decision

**Conclusion**: Principle IV fully satisfied with translation-specific nitpick handling, default implementation, and explicit exception tracking for subjective cases.

---

### ✅ Incremental and Reversible Changes (Principle V) - VALIDATED

**Pre-Implementation Compliance**:
- ✅ **Atomic Commits**: `CommitRecord` entity links to individual `TranslationChange` objects (one commit per logical change)
- ✅ **Comment ID References**: `TranslationChange.comment_id` enables traceability back to original review comment
- ✅ **Rollback Capability**: `git reset --hard` documented in error recovery workflow
- ✅ **Validation Before Commit**: `TranslationChange.validated` boolean ensures syntax checked before commit creation
- ✅ **Error Recovery**: Validation failures skip change implementation and log reasoning

**Research Validation**:
- ✅ **Commit Message Generation** (research.md): `CommitMessageTemplate` includes `comment_id` field for traceability
- ✅ **Conventional Commits**: Template system ensures each commit explains what/why for reversibility
- ✅ **GPG Signing**: Signed commits provide authenticity and non-repudiation for change tracking

**Design Enforcement**:
- ✅ **Git Operations Service**: `services/git_operations.py` implements atomic commit workflow with rollback
- ✅ **Session Manager**: `services/session_manager.py` orchestrates changes independently, enabling granular rollback
- ✅ **Commit Builder**: Each change generates separate commit message with CodeRabbitAI reference

**API Contract Validation**:
- ✅ **Commit Creation** (contracts/github-api.md): Web-Flow signing creates individual commits via GitHub API
- ✅ **Reference Updates**: Each commit updates branch reference independently, enabling rollback to any point
- ✅ **Verification**: Commit verification before proceeding to next change

**Quickstart Validation**:
- ✅ **Manual Test Run** (quickstart.md): Documentation shows atomic commit creation with traceability
- ✅ **Verify Results**: `git log --show-signature -1` command verifies individual commits
- ✅ **Rollback Example**: Troubleshooting section documents rollback procedures

**Conclusion**: Principle V fully satisfied with atomic commits, comprehensive traceability, validation gates, and documented rollback procedures.

---

### 🔒 Constitution Gate Status: ✅ PASS (Post-Design)

**Summary**: All 5 core principles validated against completed Phase 1 design artifacts:

| Principle | Pre-Implementation | Research | Design | API Contract | Quickstart |
|-----------|-------------------|----------|--------|--------------|------------|
| **I. Translation Quality First** | ✅ Classification framework | ✅ Parsers, validation | ✅ File validator | ✅ PR filtering | ✅ Test verification |
| **II. Conventional Commits** | ✅ 7 rules enforcement | ✅ Web-Flow signing | ✅ Message builder | ✅ Commit signing | ✅ Signature verification |
| **III. Translation-Only Scope** | ✅ Path patterns | ✅ Format parsers | ✅ File validator | ✅ Pattern matching | ✅ File verification |
| **IV. Nitpick Implementation** | ✅ Default implement | ✅ Classification framework | ✅ Classifier service | ✅ Label extraction | ✅ Change tracking |
| **V. Incremental Changes** | ✅ Atomic commits | ✅ Commit generation | ✅ Git operations | ✅ Individual commits | ✅ Rollback procedures |

**No Violations Detected**: All design decisions align with constitution requirements.

**Complexity Justification**: Not required - all principles satisfied without introducing complexity violations.

**Technology Alignment**:
- ✅ Python 3.11+ supports async operations for independent PR processing
- ✅ GitHub CLI provides API interactions respecting rate limits
- ✅ GitPython enables atomic git operations with rollback capability
- ✅ Docker containerization provides security isolation per constitution safety requirements
- ✅ Translation-specific parsers enforce file format validation

**Ready for Implementation**: Phase 2 (task generation via `/speckit.tasks`) can proceed with confidence in constitutional compliance.

---

## Success Validation

Post-implementation validation checklist:

### Constitution Compliance
- [ ] All commits GPG signed and verified
- [ ] Commit messages follow 7 conventional rules
- [ ] Only translation files modified (path filter validation)
- [ ] Nitpicks implemented by default (classification logic)
- [ ] Atomic commits with rollback capability

### Functional Requirements (Sample)
- [ ] FR-001: Monitors configured repositories for PRs
- [ ] FR-004: Classifies comments per constitution framework
- [ ] FR-007: Creates atomic GPG-signed commits
- [ ] FR-011: Posts summary comment to PR
- [ ] FR-016: Implements exponential backoff for API calls

### Success Criteria (Sample)
- [ ] SC-002: Processes PRs in under 5 minutes (20 comments)
- [ ] SC-003: 95% classification accuracy
- [ ] SC-004: 100% commits GPG signed
- [ ] SC-006: 100% parse errors caught before commit

### Integration Tests
- [ ] End-to-end PR processing workflow
- [ ] Multi-repository processing
- [ ] Feedback issue creation
- [ ] Error handling and rollback
- [ ] GPG signing and verification

## Next Steps

1. **Execute Phase 0 Research**: Run research agents to resolve all technology decisions
2. **Generate Phase 1 Artifacts**: Create data-model.md, contracts/, quickstart.md
3. **Run `/speckit.tasks`**: Generate dependency-ordered implementation tasks
4. **Run `/speckit.implement`**: Execute tasks to build the PR Guardian agent

## Notes

- Docker secrets mounting ensures deploy_key and gpg_bot_key remain secure
- GitHub CLI handles authentication, rate limiting, and API interactions
- Modular service architecture enables independent testing and mocking
- Constitution principles enforced at service layer (commit_builder, file_validator, comment_classifier)
- 30-minute execution window constraint drives performance requirements
