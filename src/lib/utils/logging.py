"""Structured logging utility with UTC timestamps and secret redaction."""

import logging
import re
import sys
import time
from typing import Literal


def configure_logging(
    level: int = logging.INFO,
    format_type: Literal["standard", "json"] = "standard"
) -> None:
    """
    Configure structured logging with UTC timestamps.

    Args:
        level: Logging level (default: INFO)
        format_type: Output format - "standard" or "json"
    """
    # Force UTC timestamps for all logging
    logging.Formatter.converter = time.gmtime

    if format_type == "json":
        log_format = (
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"name": "%(name)s", "message": "%(message)s"}'
        )
    else:
        log_format = "%(asctime)s UTC [%(levelname)s] %(name)s: %(message)s"

    logging.basicConfig(
        level=level,
        format=log_format,
        datefmt="%Y-%m-%dT%H:%M:%S",
        stream=sys.stdout,
        force=True
    )


def redact_secrets(text: str) -> str:
    """
    Redact tokens and secrets from text for safe logging.

    Args:
        text: Text that may contain secrets

    Returns:
        Text with secrets replaced by [REDACTED]
    """
    patterns = [
        # GitHub tokens
        (r'ghp_[a-zA-Z0-9]{36}', '[REDACTED_GH_TOKEN]'),
        (r'gho_[a-zA-Z0-9]{36}', '[REDACTED_GH_TOKEN]'),
        (r'ghu_[a-zA-Z0-9]{36}', '[REDACTED_GH_TOKEN]'),
        (r'ghs_[a-zA-Z0-9]{36}', '[REDACTED_GH_TOKEN]'),
        (r'ghr_[a-zA-Z0-9]{36}', '[REDACTED_GH_TOKEN]'),
        # Anthropic API keys
        (r'sk-ant-[a-zA-Z0-9\-_]{40,}', '[REDACTED_ANTHROPIC_KEY]'),
        # Generic API keys/tokens
        (r'(?i)(api[_-]?key|token|secret|password|auth)["\']?\s*[:=]\s*["\']?[a-zA-Z0-9\-_]{20,}',
         r'\1: [REDACTED]'),
        # Bearer tokens
        (r'Bearer\s+[a-zA-Z0-9\-_\.]+', 'Bearer [REDACTED]'),
    ]

    redacted = text
    for pattern, replacement in patterns:
        redacted = re.sub(pattern, replacement, redacted)

    return redacted


class SecretRedactingFilter(logging.Filter):
    """Logging filter that redacts secrets from log messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Redact secrets from log record message."""
        if isinstance(record.msg, str):
            record.msg = redact_secrets(record.msg)
        if record.args:
            record.args = tuple(
                redact_secrets(str(arg)) if isinstance(arg, str) else arg
                for arg in record.args
            )
        return True


def get_logger(name: str, redact: bool = True) -> logging.Logger:
    """
    Get a logger with optional secret redaction.

    Args:
        name: Logger name
        redact: Whether to enable secret redaction filter

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    if redact:
        logger.addFilter(SecretRedactingFilter())

    return logger
