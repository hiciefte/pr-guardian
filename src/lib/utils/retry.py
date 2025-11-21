"""Retry with exponential backoff using tenacity."""

import logging
from functools import wraps
from typing import Any, Callable, Type

from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

logger = logging.getLogger(__name__)


# Common retryable exceptions
class RateLimitError(Exception):
    """Raised when API rate limit is exceeded."""
    pass


class ConnectionError(Exception):
    """Raised on transient connection failures."""
    pass


class ServerError(Exception):
    """Raised on server-side errors (5xx)."""
    pass


# Default retryable exceptions
DEFAULT_RETRYABLE_EXCEPTIONS: tuple[Type[Exception], ...] = (
    RateLimitError,
    ConnectionError,
    ServerError,
    TimeoutError,
)


def retry_with_backoff(
    max_attempts: int = 5,
    min_wait: float = 2.0,
    max_wait: float = 60.0,
    retryable_exceptions: tuple[Type[Exception], ...] | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator for retry with exponential backoff and jitter.

    Uses tenacity for robust retry logic with:
    - Exponential backoff: 2^attempt seconds base wait
    - Jitter: Random 0-1 second added to prevent thundering herd
    - Configurable max attempts and wait bounds

    Args:
        max_attempts: Maximum number of retry attempts (default: 5)
        min_wait: Minimum wait time in seconds (default: 2.0)
        max_wait: Maximum wait time in seconds (default: 60.0)
        retryable_exceptions: Tuple of exception types to retry on

    Returns:
        Decorator function

    Example:
        @retry_with_backoff(max_attempts=3)
        def call_api():
            response = requests.get(url)
            if response.status_code == 429:
                raise RateLimitError("Rate limited")
            return response.json()
    """
    if retryable_exceptions is None:
        retryable_exceptions = DEFAULT_RETRYABLE_EXCEPTIONS

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @retry(
            retry=retry_if_exception_type(retryable_exceptions),
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential_jitter(initial=min_wait, max=max_wait, jitter=1),
            before_sleep=lambda retry_state: logger.warning(
                f"Retry attempt {retry_state.attempt_number}/{max_attempts} "
                f"for {func.__name__} after {retry_state.outcome.exception()}"
            ),
            reraise=True,
        )
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        return wrapper

    return decorator


def is_retryable_error(error: Exception) -> bool:
    """
    Check if an error is retryable.

    Args:
        error: The exception to check

    Returns:
        True if the error is retryable
    """
    return isinstance(error, DEFAULT_RETRYABLE_EXCEPTIONS)
