# Quickstart Guide: PR Guardian

**Phase**: 1 (Design)
**Date**: 2025-10-24
**Status**: Complete
**Feature**: [spec.md](./spec.md) | [plan.md](./plan.md)

## Overview

This guide provides step-by-step instructions to build, configure, and run PR Guardian in Docker. Follow these instructions to set up the autonomous translation PR review agent from scratch.

---

## Prerequisites

### Required Software

- **Docker**: Version 20.10+ with BuildKit support
- **Docker Compose**: Version 2.0+
- **Git**: Version 2.30+ with GPG support (if using traditional GPG signing)
- **GitHub Account**: With access to monitored repositories

### Required Access

- **GitHub Personal Access Token** with scopes:
  - `repo` (full repository access)
  - `write:discussion` (PR comment permissions)
- **SSH Deploy Keys** for each monitored repository (read-write access)
- **GPG Bot Key** for commit signing (or use GitHub Web-Flow signing)

---

## Step 1: Repository Setup

### Clone Repository

```bash
# Clone PR Guardian repository
git clone https://github.com/your-org/pr-guardian.git
cd pr-guardian

# Verify you're on main branch
git branch --show-current
```

### Project Structure

```
pr-guardian/
├── src/                    # Application source code
│   ├── models/            # Data models
│   ├── services/          # Business logic
│   ├── cli/               # CLI interface
│   └── lib/               # Utilities
├── tests/                 # Test suite
│   ├── contract/          # API contract tests
│   ├── integration/       # Integration tests
│   └── unit/              # Unit tests
├── docker/                # Docker configuration
│   ├── Dockerfile
│   ├── entrypoint.sh
│   └── docker-compose.yml
├── config/                # Configuration templates
│   ├── config.example.yml
│   └── .env.example
├── secrets/               # Secrets directory (NOT in git)
│   ├── deploy_key         # SSH private key
│   ├── deploy_key.pub     # SSH public key
│   └── gpg_bot_key        # GPG private key (if using traditional signing)
└── .specify/              # Spec-Kit artifacts
    └── memory/
        └── constitution.md
```

---

## Step 2: Secret Configuration

### Create Secrets Directory

```bash
# Create secrets directory (ignored by git)
mkdir -p secrets
chmod 700 secrets
```

### Generate SSH Deploy Key

```bash
# Generate ed25519 SSH key pair
ssh-keygen -t ed25519 -C "pr-guardian-deploy-key" -f secrets/deploy_key -N ""

# Set correct permissions
chmod 600 secrets/deploy_key
chmod 644 secrets/deploy_key.pub

# Display public key for GitHub configuration
cat secrets/deploy_key.pub
```

**Add Deploy Key to GitHub**:

For EACH monitored repository:

1. Navigate to: `https://github.com/owner/repository/settings/keys`
2. Click "Add deploy key"
3. **Title**: `PR Guardian Bot`
4. **Key**: Paste contents of `secrets/deploy_key.pub`
5. ✅ **Allow write access** (required for pushing commits)
6. Click "Add key"

⚠️ **Important**: Use unique deploy keys per repository for security (do NOT reuse)

### GitHub Personal Access Token

```bash
# Create .env file from template
cp config/.env.example .env

# Edit .env and add your GitHub token
nano .env
```

**.env**:
```bash
# GitHub Authentication
GH_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Healthchecks.io (optional)
HEALTHCHECK_URL=https://hc-ping.com/your-uuid-here
```

**Generate GitHub Token**:

1. Go to: `https://github.com/settings/tokens/new`
2. **Note**: `PR Guardian Bot`
3. **Scopes**:
   - ✅ `repo` (Full control of private repositories)
   - ✅ `write:discussion` (Read and write discussions)
4. Click "Generate token"
5. Copy token and paste into `.env` file

### Anthropic API Key *(Added 2025-10-24)*

PR Guardian uses Anthropic Claude 3 Haiku for natural language comment parsing.

**Generate Anthropic API Key**:

1. Visit: `https://console.anthropic.com/`
2. Navigate to **Settings** → **API Keys**
3. Click **"Create Key"**
4. **Name**: `PR Guardian Production`
5. **Workspace**: Select appropriate workspace
6. Click **"Create Key"**
7. ⚠️ **Copy immediately** (shown only once)

**Add to .env**:
```bash
nano .env
```

**.env** (updated):
```bash
# GitHub Authentication
GH_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Anthropic LLM API (for comment parsing)
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# LLM Configuration (optional, defaults shown)
LLM_MODEL=claude-3-haiku-20240307
LLM_MAX_TOKENS=500
LLM_CONFIDENCE_THRESHOLD=0.80

# Healthchecks.io (optional)
HEALTHCHECK_URL=https://hc-ping.com/your-uuid-here
```

**Expected Costs**:
- **Base**: $0.95-2.40/month for 6,000 requests (200 comments/day)
- **Optimized**: $1.13/month with prompt caching + semantic caching
- **Monitor usage**: https://console.anthropic.com/settings/usage

**LLM Configuration Parameters**:
- `LLM_MODEL`: Claude model version (default: `claude-3-haiku-20240307`)
- `LLM_MAX_TOKENS`: Max output tokens per request (default: `500`)
- `LLM_CONFIDENCE_THRESHOLD`: Auto-implement threshold (default: `0.80`, range: 0.60-1.00)
  - `≥ 0.80`: Auto-implement translation change
  - `0.60-0.79`: Flag for human review
  - `< 0.60`: Skip extraction (low confidence)

### GPG Bot Key (Optional - Traditional Signing)

If using GitHub Web-Flow signing (recommended), skip this section.

For traditional GPG signing:

```bash
# Generate passphrase-less GPG key
cat > secrets/gpg-key-config <<EOF
%no-protection
Key-Type: RSA
Key-Length: 4096
Subkey-Type: RSA
Subkey-Length: 4096
Name-Real: PR Guardian Bot
Name-Email: pr-guardian@example.com
Expire-Date: 1y
EOF

# Generate key
gpg --batch --generate-key secrets/gpg-key-config

# Export private key
gpg --export-secret-keys --armor pr-guardian@example.com > secrets/gpg_bot_key

# Set permissions
chmod 600 secrets/gpg_bot_key

# Get public key for GitHub
gpg --export --armor pr-guardian@example.com
```

**Add GPG Key to GitHub**:

1. Go to: `https://github.com/settings/keys`
2. Click "New GPG key"
3. Paste public key (from command above)
4. Click "Add GPG key"

---

## Step 3: Configuration

### Create Configuration File

```bash
# Copy example configuration
cp config/config.example.yml config/config.yml

# Edit configuration
nano config/config.yml
```

**config/config.yml**:

```yaml
# PR Guardian Configuration

# GitHub Settings
github:
  token_env: GH_TOKEN  # Environment variable name
  target_username: translation-bot  # GitHub user to monitor

# Monitored Repositories
repositories:
  - owner: bisq-network
    repository: bisq-mobile
    branch_filter: main  # Only PRs targeting main branch
    enabled: true

  - owner: bisq-network
    repository: bisq2
    branch_filter: main
    enabled: true

# Feedback Repository (for issue creation)
feedback:
  repository: bisq-network/translation-automation
  enabled: true

# Execution Settings
execution:
  max_comments_per_pr: 50
  timeout_seconds: 1800  # 30 minutes
  schedule: "0 2 * * *"  # Daily at 02:00 UTC

# Signing Configuration
signing:
  method: web-flow  # Options: web-flow, gpg
  gpg_key_path: /secrets/gpg_bot_key  # Only if method=gpg
  deploy_key_path: /root/.ssh/id_ed25519

# Translation File Patterns
translation_patterns:
  - "*.properties"
  - "**/i18n/**/*.json"
  - "**/locales/**/*.yml"
  - "**/locales/**/*.yaml"
  - "**/lang/**/*"

# Logging
logging:
  level: INFO  # DEBUG, INFO, WARNING, ERROR
  format: structured  # structured or simple
```

---

## Step 4: Docker Build

### Build Docker Image

```bash
# Build using Docker Compose
docker-compose build

# Or build directly with Docker
docker build -f docker/Dockerfile -t pr-guardian:latest .
```

**Dockerfile** (docker/Dockerfile):

```dockerfile
# PR Guardian - Translation Review Agent
FROM python:3.11-alpine

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=UTC

# Install system dependencies
RUN apk add --no-cache \
    git \
    openssh-client \
    gnupg \
    github-cli \
    curl

# Create app directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ src/
COPY .specify/ .specify/

# Create .ssh directory for deploy key
RUN mkdir -p /root/.ssh && chmod 700 /root/.ssh

# Add GitHub known hosts
RUN ssh-keyscan github.com >> /root/.ssh/known_hosts

# Copy entrypoint script
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Set entrypoint
ENTRYPOINT ["/entrypoint.sh"]

# Default command
CMD ["python", "-m", "src.cli.main", "run"]
```

**Entrypoint Script** (docker/entrypoint.sh):

```bash
#!/bin/sh
set -e

# Configure SSH for git operations
if [ -f /root/.ssh/id_ed25519 ]; then
    chmod 600 /root/.ssh/id_ed25519
    git config --global core.sshCommand "ssh -i /root/.ssh/id_ed25519 -o StrictHostKeyChecking=yes"
fi

# Import GPG key if using traditional signing
if [ "$SIGNING_METHOD" = "gpg" ] && [ -f /secrets/gpg_bot_key ]; then
    gpg --batch --import /secrets/gpg_bot_key
    GPG_KEY_ID=$(gpg --list-secret-keys --keyid-format LONG | grep sec | awk '{print $2}' | cut -d'/' -f2)
    git config --global user.signingkey "$GPG_KEY_ID"
    git config --global commit.gpgsign true
fi

# Configure GitHub CLI authentication
if [ -n "$GH_TOKEN" ]; then
    gh auth status || echo "Warning: GitHub CLI authentication may not be configured"
fi

# Execute main command
exec "$@"
```

**Docker Compose** (docker/docker-compose.yml):

```yaml
version: '3.8'

services:
  pr-guardian:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    container_name: pr-guardian
    volumes:
      - ../secrets/deploy_key:/root/.ssh/id_ed25519:ro
      - ../secrets/gpg_bot_key:/secrets/gpg_bot_key:ro
      - ../config/config.yml:/app/config/config.yml:ro
    env_file:
      - ../config/.env
    environment:
      - TZ=UTC
      - SIGNING_METHOD=web-flow
      # Redis connection (optional, for semantic caching)
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - REDIS_ENABLED=true  # Set to false to disable semantic caching
    depends_on:
      - redis  # Optional: remove if not using semantic caching
    labels:
      # Ofelia scheduler configuration
      ofelia.enabled: "true"
      ofelia.job-exec.pr-guardian-daily.schedule: "0 2 * * *"
      ofelia.job-exec.pr-guardian-daily.command: "python -m src.cli.main run"
      ofelia.job-exec.pr-guardian-daily.no-overlap: "true"

  # Redis cache (optional - for LLM semantic caching)
  # Provides 20-40% cache hit rate for similar comments
  # Additional 30% cost reduction (~$0.67/month vs $1.13/month)
  redis:
    image: redis:7-alpine
    container_name: pr-guardian-redis
    command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
    volumes:
      - redis-data:/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 3s
      retries: 3

  # Ofelia scheduler (optional - for Docker-based scheduling)
  ofelia:
    image: mcuadros/ofelia:latest
    container_name: ofelia-scheduler
    depends_on:
      - pr-guardian
    command: daemon --docker
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
    restart: unless-stopped

volumes:
  redis-data:  # Persistent Redis storage
```

**Redis Semantic Caching** *(Optional)*:
- **Purpose**: Cache LLM extraction results for similar comments across PRs
- **Cache TTL**: 7 days (covers weekly translation PR cycles)
- **Expected Hit Rate**: 20-40% (similar terminology/phrasing patterns)
- **Cost Savings**: Additional 30% reduction in API calls (~$0.67/month)
- **Memory**: 256MB limit with LRU eviction policy
- **To Disable**: Set `REDIS_ENABLED=false` in environment or remove `redis` service

---

## Step 5: First Execution

### Manual Test Run

```bash
# Run PR Guardian manually to verify setup
docker-compose run --rm pr-guardian

# Or using Docker directly
docker run --rm \
  -v $(pwd)/secrets/deploy_key:/root/.ssh/id_ed25519:ro \
  -v $(pwd)/secrets/gpg_bot_key:/secrets/gpg_bot_key:ro \
  -v $(pwd)/config/config.yml:/app/config/config.yml:ro \
  --env-file config/.env \
  pr-guardian:latest
```

**Expected Output** *(Updated with LLM integration)*:

```
2024-10-24 02:30:00 UTC [INFO] PR Guardian execution started
2024-10-24 02:30:01 UTC [INFO] Loaded configuration from /app/config/config.yml
2024-10-24 02:30:01 UTC [INFO] Monitoring 2 repositories
2024-10-24 02:30:02 UTC [INFO] GitHub authentication verified: pr-guardian-bot
2024-10-24 02:30:02 UTC [INFO] Anthropic API authenticated successfully (model: claude-3-haiku-20240307)
2024-10-24 02:30:02 UTC [INFO] Redis semantic cache enabled (host: redis:6379)
2024-10-24 02:30:03 UTC [INFO] Processing repository: bisq-network/bisq-mobile
2024-10-24 02:30:04 UTC [INFO] Discovered 1 open PR by translation-bot
2024-10-24 02:30:05 UTC [INFO] PR #868: Update Spanish and German translations
2024-10-24 02:30:06 UTC [INFO] Retrieved 18 CodeRabbitAI comments
2024-10-24 02:30:07 UTC [INFO] Parsing comments with LLM (parallel: 10 concurrent)
2024-10-24 02:30:10 UTC [INFO] LLM extraction complete: 18 processed, 3 cache hits (16.7%), avg confidence: 0.82
2024-10-24 02:30:10 UTC [INFO] Implementation decisions: 15 auto-implement, 2 human-review, 1 skipped (low confidence)
2024-10-24 02:30:11 UTC [INFO] Classified 15 implementable comments: 2 Critical, 5 Constructive, 8 Nitpicks
2024-10-24 02:30:15 UTC [INFO] Implementing 15 changes
2024-10-24 02:35:00 UTC [INFO] Created 15 signed commits
2024-10-24 02:35:30 UTC [INFO] Pushed commits to PR #868
2024-10-24 02:36:00 UTC [INFO] Posted summary comment to PR #868 (including 2 human-review items)
2024-10-24 02:36:30 UTC [INFO] Created feedback issue #456 in translation-automation
2024-10-24 02:36:31 UTC [INFO] LLM costs this session: $0.08 (input: 4,410 tokens, output: 1,404 tokens)
2024-10-24 02:38:45 UTC [INFO] PR Guardian execution completed in 525.0s
```

### Verify Results

1. **Check PR for commits**:
   ```bash
   gh pr view 868 --repo bisq-network/bisq-mobile --json commits
   ```

2. **Verify commit signatures**:
   ```bash
   git clone git@github.com:bisq-network/bisq-mobile.git /tmp/test-repo
   cd /tmp/test-repo
   git log --show-signature -1
   ```

3. **Check feedback issue**:
   ```bash
   gh issue view 456 --repo bisq-network/translation-automation
   ```

---

## Step 6: Scheduled Execution

### Option 1: Docker Compose with Ofelia (Recommended)

Already configured in `docker-compose.yml`:

```bash
# Start scheduler
docker-compose up -d ofelia

# View logs
docker-compose logs -f ofelia

# Check scheduled jobs
docker exec ofelia ofelia config
```

**Ofelia will**:
- Execute `pr-guardian` daily at 02:00 UTC
- Prevent overlapping executions
- Log all output

### Option 2: Host Cron

```bash
# Edit crontab
crontab -e

# Add PR Guardian job
0 2 * * * cd /opt/pr-guardian && docker-compose run --rm pr-guardian >> /var/log/pr-guardian.log 2>&1
```

### Option 3: Systemd Timer

Create systemd service:

```bash
# /etc/systemd/system/pr-guardian.service
[Unit]
Description=PR Guardian Translation Review Agent
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
WorkingDirectory=/opt/pr-guardian
ExecStart=/usr/local/bin/docker-compose run --rm pr-guardian
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Create systemd timer:

```bash
# /etc/systemd/system/pr-guardian.timer
[Unit]
Description=PR Guardian Daily Execution
Requires=pr-guardian.service

[Timer]
OnCalendar=*-*-* 02:00:00 UTC
Persistent=true

[Install]
WantedBy=timers.target
```

Enable timer:

```bash
sudo systemctl daemon-reload
sudo systemctl enable pr-guardian.timer
sudo systemctl start pr-guardian.timer
sudo systemctl status pr-guardian.timer
```

---

## Step 7: Monitoring

### Healthchecks.io Integration (Recommended)

1. Sign up at [healthchecks.io](https://healthchecks.io)
2. Create new check: "PR Guardian Daily"
3. Period: 25 hours (allows 1-hour grace after 24h schedule)
4. Copy ping URL

Add to `.env`:

```bash
HEALTHCHECK_URL=https://hc-ping.com/your-uuid-here
```

PR Guardian will ping healthchecks.io on success/failure.

### Log Monitoring

**Docker Compose logs**:

```bash
# View recent logs
docker-compose logs pr-guardian --tail=100

# Follow logs in real-time
docker-compose logs -f pr-guardian

# Filter by log level
docker-compose logs pr-guardian | grep ERROR
```

**Host cron logs**:

```bash
# View cron output
tail -f /var/log/pr-guardian.log

# Search for errors
grep -i error /var/log/pr-guardian.log
```

**Systemd journal**:

```bash
# View service logs
journalctl -u pr-guardian.service -f

# Recent failures
journalctl -u pr-guardian.service --since today --priority err
```

---

## Troubleshooting

### Common Issues

#### Issue: "Authentication failed"

**Symptoms**:
```
ERROR: gh auth status failed
ERROR: You are not logged into any GitHub hosts
```

**Solution**:
```bash
# Verify GH_TOKEN in .env
cat config/.env | grep GH_TOKEN

# Test authentication
docker run --rm --env-file config/.env pr-guardian:latest gh auth status

# Regenerate token if expired
# Visit: https://github.com/settings/tokens
```

---

#### Issue: "Permission denied (publickey)"

**Symptoms**:
```
ERROR: Permission denied (publickey).
ERROR: fatal: Could not read from remote repository
```

**Solution**:
```bash
# Verify deploy key permissions
ls -l secrets/deploy_key
# Should be: -rw------- (600)

# Fix permissions
chmod 600 secrets/deploy_key

# Verify deploy key added to GitHub
# Check: https://github.com/owner/repository/settings/keys
```

---

#### Issue: "Commit signature verification failed"

**Symptoms**:
```
ERROR: gpg: signing failed: No secret key
ERROR: git commit -S failed
```

**Solution for Web-Flow**:
```yaml
# Ensure signing method is web-flow in config.yml
signing:
  method: web-flow
```

**Solution for GPG**:
```bash
# Verify GPG key imported
docker exec pr-guardian gpg --list-secret-keys

# Re-import if missing
docker exec pr-guardian gpg --batch --import /secrets/gpg_bot_key

# Check key expiration
gpg --list-keys pr-guardian@example.com
```

---

#### Issue: "Rate limit exceeded"

**Symptoms**:
```
ERROR: API rate limit exceeded
ERROR: HTTP 403: rate limit
```

**Solution**:
```bash
# Check current rate limit
gh api rate_limit

# Wait for limit reset (shown in response)
# Or reduce max_comments_per_pr in config.yml

# Verify exponential backoff is working
docker-compose logs pr-guardian | grep -i "rate limit"
```

---

#### Issue: "Anthropic API authentication failed" *(Added 2025-10-24)*

**Symptoms**:
```
ERROR: Anthropic API authentication failed: 401 Unauthorized
ERROR: Invalid API key provided
```

**Solution**:
```bash
# Verify ANTHROPIC_API_KEY in .env
cat config/.env | grep ANTHROPIC_API_KEY

# Test authentication
docker run --rm --env-file config/.env pr-guardian:latest python -c "
from anthropic import Anthropic
import os
client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
response = client.messages.create(model='claude-3-haiku-20240307', max_tokens=10, messages=[{'role': 'user', 'content': 'Test'}])
print('✓ Anthropic API authenticated successfully')
"

# Regenerate API key if invalid
# Visit: https://console.anthropic.com/settings/keys
```

---

#### Issue: "LLM rate limit exceeded" *(Added 2025-10-24)*

**Symptoms**:
```
ERROR: Anthropic rate limit exceeded: 429 Too Many Requests
WARNING: Retrying in 60 seconds (attempt 2/3)
```

**Solution**:
```bash
# Check current API tier and limits
# Visit: https://console.anthropic.com/settings/limits

# Reduce concurrency in code (default: 10 concurrent)
# Edit src/services/llm_parser.py: semaphore = asyncio.Semaphore(5)

# Or wait for rate limit reset (automatic retry with exponential backoff)
docker-compose logs pr-guardian | grep -i "anthropic\|rate limit"

# Monitor usage
# Visit: https://console.anthropic.com/settings/usage
```

---

#### Issue: "LLM extraction low confidence" *(Added 2025-10-24)*

**Symptoms**:
```
WARNING: Low confidence extraction (0.45) for comment ID 1234567890, skipping
INFO: Implementation decisions: 10 auto-implement, 5 human-review, 3 skipped (low confidence)
```

**Solution**:
```bash
# Review skipped comments in session report
# Low confidence indicates ambiguous comment text

# Lower confidence threshold to capture more extractions (default: 0.80)
nano config/.env
# Add: LLM_CONFIDENCE_THRESHOLD=0.70

# Or keep threshold high and manually review skipped comments
# Skipped comments logged with reasoning for manual action
```

---

#### Issue: "Redis connection failed" *(Added 2025-10-24)*

**Symptoms**:
```
WARNING: Redis connection failed: Could not connect to Redis at redis:6379
INFO: Semantic caching disabled, falling back to direct LLM calls
```

**Solution**:
```bash
# Check Redis container status
docker ps | grep redis

# Start Redis if not running
docker-compose up -d redis

# Test Redis connection
docker exec pr-guardian-redis redis-cli ping
# Should return: PONG

# Check Redis logs
docker-compose logs redis

# Disable semantic caching if Redis not needed
nano config/.env
# Set: REDIS_ENABLED=false
```

---

#### Issue: "No PRs discovered"

**Symptoms**:
```
INFO: Discovered 0 open PRs by translation-bot
INFO: Execution completed with no work
```

**Solution**:
```bash
# Verify target username in config.yml
cat config/config.yml | grep target_username

# Check for open PRs manually
gh pr list --repo owner/repository --author translation-bot --state open

# Verify repository access
gh repo view owner/repository
```

---

#### Issue: "Translation file not found"

**Symptoms**:
```
ERROR: File not found: src/i18n/es_ES.json
ERROR: Failed to parse translation file
```

**Solution**:
```bash
# Verify translation patterns in config.yml
cat config/config.yml | grep -A 5 translation_patterns

# Check PR files manually
gh pr view 868 --json files

# Update patterns if needed to match repository structure
```

---

### Debug Mode

Run PR Guardian with debug logging:

```bash
# Set log level to DEBUG in config.yml
nano config/config.yml
# logging:
#   level: DEBUG

# Run with debug output
docker-compose run --rm pr-guardian
```

---

## Testing

### Run Test Suite

```bash
# Run all tests
docker-compose run --rm pr-guardian pytest

# Run specific test categories
docker-compose run --rm pr-guardian pytest tests/unit/
docker-compose run --rm pr-guardian pytest tests/integration/
docker-compose run --rm pr-guardian pytest tests/contract/

# Run with coverage
docker-compose run --rm pr-guardian pytest --cov=src --cov-report=html
```

### Manual Integration Test

```bash
# 1. Create test PR with translations
gh pr create --repo your-test-org/test-repo \
  --title "Test translation PR" \
  --body "Test PR for PR Guardian"

# 2. Add CodeRabbitAI-style comments
gh pr comment <PR_NUMBER> --body "nitpick: Test comment"

# 3. Run PR Guardian
docker-compose run --rm pr-guardian

# 4. Verify commits created
gh pr view <PR_NUMBER> --json commits

# 5. Verify signature
git log --show-signature -1
```

---

## Maintenance

### Update PR Guardian

```bash
# Pull latest changes
git pull origin main

# Rebuild Docker image
docker-compose build

# Restart scheduler (if using Ofelia)
docker-compose restart ofelia
```

### Rotate Secrets

#### Rotate GitHub Token:

```bash
# Generate new token: https://github.com/settings/tokens
nano config/.env
# Update GH_TOKEN=ghp_NEW_TOKEN

# Restart scheduler
docker-compose restart ofelia
```

#### Rotate Deploy Key:

```bash
# Generate new key
ssh-keygen -t ed25519 -C "pr-guardian-deploy-key-2" -f secrets/deploy_key_new -N ""

# Add new key to GitHub
cat secrets/deploy_key_new.pub
# Visit: https://github.com/owner/repository/settings/keys

# Replace old key
mv secrets/deploy_key secrets/deploy_key.old
mv secrets/deploy_key_new secrets/deploy_key
chmod 600 secrets/deploy_key

# Test new key
docker-compose run --rm pr-guardian

# Remove old key from GitHub after verification
```

#### Rotate GPG Key (if using traditional signing):

```bash
# Generate new key (see Step 2)
gpg --export --armor pr-guardian-new@example.com

# Add to GitHub: https://github.com/settings/keys

# Export and replace
gpg --export-secret-keys --armor pr-guardian-new@example.com > secrets/gpg_bot_key

# Update config.yml if email changed
# Restart scheduler
```

---

## Next Steps

1. **Monitor First Week**: Watch logs and healthchecks for any issues
2. **Tune Configuration**: Adjust `max_comments_per_pr` based on workload
3. **Review Feedback Issues**: Check translation-automation repo for patterns
4. **Scale Repositories**: Add more monitored repositories as needed
5. **Customize Classification**: Update constitution if classification needs adjustment

---

## Support

### Resources

- **Documentation**: [spec.md](./spec.md), [plan.md](./plan.md)
- **Constitution**: `.specify/memory/constitution.md`
- **GitHub Issues**: https://github.com/your-org/pr-guardian/issues
- **Research**: [research.md](./research.md)

### Common Commands Reference

```bash
# Configuration
cat config/config.yml                    # View configuration
nano config/config.yml                   # Edit configuration
docker-compose config                    # Validate docker-compose.yml

# Execution
docker-compose run --rm pr-guardian      # Manual run
docker-compose logs -f pr-guardian       # View logs
docker-compose ps                        # Check running containers

# Secrets
ls -la secrets/                          # List secret files
chmod 600 secrets/deploy_key             # Fix key permissions
cat secrets/deploy_key.pub               # View public key

# GitHub
gh auth status                           # Check authentication
gh pr list --repo owner/repo             # List PRs
gh api rate_limit                        # Check rate limit

# Docker
docker-compose build                     # Rebuild image
docker-compose up -d                     # Start services
docker-compose down                      # Stop services
docker system prune -a                   # Clean up Docker
```

---

## Summary

You now have PR Guardian configured and running! The agent will:

✅ Run daily at 02:00 UTC
✅ Monitor configured repositories for translation PRs
✅ Classify and implement CodeRabbitAI comments
✅ Create GPG-signed atomic commits
✅ Post summary comments to PRs
✅ Create feedback issues for translation system improvements

**Healthy execution indicators**:
- Log messages show "execution completed"
- Healthchecks.io shows green status
- PRs have signed commits pushed
- Feedback issues created in translation-automation repo

**If you encounter issues**, refer to the Troubleshooting section or create a GitHub issue with logs and configuration (redact secrets!).
