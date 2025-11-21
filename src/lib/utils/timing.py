"""UTC timing utilities for consistent timezone handling."""

import os
import time
from datetime import datetime, timezone


def ensure_utc_timezone() -> None:
    """
    Enforce UTC timezone for all operations.

    Sets TZ environment variable and configures logging
    to use UTC timestamps.
    """
    import logging

    # Set environment variable
    os.environ["TZ"] = "UTC"

    # Configure logging timestamps in UTC
    logging.Formatter.converter = time.gmtime


def utc_now() -> datetime:
    """
    Get current UTC time as timezone-aware datetime.

    Returns:
        Timezone-aware datetime in UTC

    Example:
        now = utc_now()
        print(now.isoformat())  # 2024-01-15T10:30:00+00:00
    """
    return datetime.now(timezone.utc)


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Human-readable duration string

    Examples:
        format_duration(0.5)      # "500ms"
        format_duration(45)       # "45.0s"
        format_duration(125)      # "2m 5s"
        format_duration(3725)     # "1h 2m 5s"
    """
    if seconds < 1:
        return f"{int(seconds * 1000)}ms"

    if seconds < 60:
        return f"{seconds:.1f}s"

    minutes, secs = divmod(int(seconds), 60)

    if minutes < 60:
        return f"{minutes}m {secs}s"

    hours, mins = divmod(minutes, 60)
    return f"{hours}h {mins}m {secs}s"


def parse_iso_datetime(iso_string: str) -> datetime:
    """
    Parse ISO 8601 datetime string to timezone-aware UTC datetime.

    Args:
        iso_string: ISO 8601 formatted datetime string

    Returns:
        Timezone-aware datetime in UTC

    Example:
        dt = parse_iso_datetime("2024-01-15T10:30:00Z")
    """
    # Handle 'Z' suffix (UTC indicator)
    if iso_string.endswith('Z'):
        iso_string = iso_string[:-1] + '+00:00'

    dt = datetime.fromisoformat(iso_string)

    # If naive datetime, assume UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        # Convert to UTC
        dt = dt.astimezone(timezone.utc)

    return dt


def format_iso_utc(dt: datetime) -> str:
    """
    Format datetime to ISO 8601 UTC string.

    Args:
        dt: Datetime to format

    Returns:
        ISO 8601 formatted string with Z suffix

    Example:
        s = format_iso_utc(utc_now())  # "2024-01-15T10:30:00Z"
    """
    # Ensure UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)

    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
