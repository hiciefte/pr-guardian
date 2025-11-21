# PR Guardian

Autonomous Translation PR Review Agent - automatically implements CodeRabbitAI review comments on translation PRs.

## Overview

PR Guardian is a Docker-based agent that:

1. **Monitors** GitHub repositories for translation PRs by a configured author
2. **Retrieves** CodeRabbitAI review comments
3. **Parses** comments using Claude 3 Haiku to extract translation changes
4. **Classifies** comments as Critical, Constructive, or Nitpick
5. **Implements** changes by modifying translation files
6. **Creates** GPG-signed commits following conventional commit standards
7. **Pushes** commits to the PR
8. **Posts** summary comments with implementation status
9. **Creates** feedback issues for translation system improvements

## Quick Start

### Prerequisites

- Docker 20.10+ with Docker Compose
- GitHub Personal Access Token (repo, write:discussion scopes)
- Anthropic API Key for LLM parsing
- SSH deploy keys for monitored repositories

### Setup

```bash
# Clone repository
git clone https://github.com/your-org/pr-guardian.git
cd pr-guardian

# Create secrets directory
mkdir -p secrets
chmod 700 secrets

# Generate SSH deploy key
ssh-keygen -t ed25519 -C "pr-guardian" -f secrets/deploy_key -N ""

# Configure environment
cp config/.env.example config/.env
# Edit config/.env with your tokens

# Configure agent
cp config/config.example.yml config/config.yml
# Edit config/config.yml with your repositories

# Build and run
docker compose -f docker/docker-compose.yml build
docker compose -f docker/docker-compose.yml run --rm pr-guardian
```

### Configuration

**config/.env**:
```bash
GH_TOKEN=ghp_xxxxxxxxxxxx
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxx
```

**config/config.yml**:
```yaml
github:
  token_env: GH_TOKEN
  target_username: translation-bot

repositories:
  - owner: your-org
    repository: your-repo
    branch_filter: main
    enabled: true

feedback:
  repository: your-org/translation-automation
  enabled: true
```

## Usage

### Manual Execution

```bash
# Run agent
docker compose -f docker/docker-compose.yml run --rm pr-guardian

# Dry run (no changes made)
docker compose -f docker/docker-compose.yml run --rm pr-guardian python -m src.cli.main run --dry-run

# Verbose logging
docker compose -f docker/docker-compose.yml run --rm pr-guardian python -m src.cli.main run --verbose
```

### Scheduled Execution

Using Docker Compose with Ofelia (included):

```bash
# Start scheduler
docker compose -f docker/docker-compose.yml up -d ofelia

# View logs
docker compose -f docker/docker-compose.yml logs -f ofelia
```

Default schedule: Daily at 02:00 UTC

## Architecture

```
src/
├── models/           # Pydantic data models
├── services/         # Business logic
│   ├── config_loader.py
│   ├── github_client.py
│   ├── pr_discovery.py
│   ├── comment_retrieval.py
│   ├── llm_parser.py
│   ├── comment_classifier.py
│   ├── translation_processor.py
│   ├── commit_builder.py
│   ├── git_operations.py
│   ├── gpg_signer.py
│   ├── session_manager.py
│   ├── feedback_aggregator.py
│   ├── issue_creator.py
│   └── summary_poster.py
├── cli/              # CLI interface
└── lib/              # Utilities
    ├── parsers/      # Translation file parsers
    ├── validators/   # Validation utilities
    └── utils/        # Common utilities
```

## Comment Classification

Based on the constitution framework:

| Type | Priority | Action | Examples |
|------|----------|--------|----------|
| **Critical** | 1 | Always implement | Placeholder errors, syntax issues |
| **Constructive** | 2 | Implement | Terminology improvements, formality |
| **Nitpick** | 3 | Implement (skip if conflicts) | Punctuation, style preferences |

## Translation File Support

- Java .properties
- JSON
- YAML

## Commit Message Format

Follows [7 rules of great commit messages](https://cbea.ms/git-commit/):

```
Fix Spanish translation: incorrect placeholder variable

What: Changed {usuario} to {user} to match source key
Why: CodeRabbitAI identified placeholder variable mismatch
CodeRabbitAI-Comment-ID: 12345
Locale: es_ES
```

## LLM Integration

Uses Anthropic Claude 3 Haiku for natural language comment parsing:

- **Cost**: ~$1.13-2.40/month for 6,000 requests
- **Confidence thresholds**:
  - ≥0.80: Auto-implement
  - 0.60-0.79: Flag for human review
  - <0.60: Skip extraction

## Feedback Issues

Automatically creates GitHub issues summarizing feedback patterns:

- Pattern types: terminology, punctuation, formality, grammar, placeholders
- Severity classification: critical, moderate, minor
- Improvement recommendations
- Affected locales

## Development

```bash
# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check .

# Format
black .

# Type check
mypy src/
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GH_TOKEN` | Yes | GitHub Personal Access Token |
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key for LLM |
| `SIGNING_METHOD` | No | `web-flow` (default) or `gpg` |
| `REDIS_ENABLED` | No | Enable semantic caching (default: true) |
| `HEALTHCHECK_URL` | No | Healthchecks.io ping URL |

## Monitoring

- **Healthchecks.io**: Configure `HEALTHCHECK_URL` for execution monitoring
- **Logs**: JSON-structured logs with UTC timestamps
- **Metrics**: Session reports with execution statistics

## License

MIT
