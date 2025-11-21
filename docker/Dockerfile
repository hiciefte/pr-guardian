# PR Guardian - Autonomous Translation PR Review Agent
# syntax=docker/dockerfile:1

FROM python:3.11-alpine

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=UTC \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apk add --no-cache \
    git \
    openssh-client \
    gnupg \
    github-cli \
    curl \
    tzdata

# Create app directory
WORKDIR /app

# Create .ssh directory for deploy key
RUN mkdir -p /root/.ssh && chmod 700 /root/.ssh

# Add GitHub known hosts
RUN ssh-keyscan github.com >> /root/.ssh/known_hosts 2>/dev/null

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ src/
COPY pyproject.toml .

# Copy entrypoint script
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Create non-root user for security (optional, currently running as root for GPG/SSH)
# RUN adduser -D -u 1000 prguardian && chown -R prguardian:prguardian /app
# USER prguardian

# Health check - increased start-period to allow for initialization
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD gh auth status || exit 1

# Set entrypoint
ENTRYPOINT ["/entrypoint.sh"]

# Default command
CMD ["python", "-m", "src.cli.main", "run"]
