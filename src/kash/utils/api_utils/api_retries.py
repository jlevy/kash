from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from kash.utils.api_utils.http_utils import extract_http_status_code


class HTTPRetryBehavior(Enum):
    """HTTP status code retry behavior classification."""

    FULL = "full"
    """Fully retry these status codes (e.g., 429, 500, 502, 503, 504)"""

    CONSERVATIVE = "conservative"
    """Retry conservatively: may indicate rate limiting or temporary issues (e.g., 403, 408)"""

    NEVER = "never"
    """Never retry these status codes (e.g., 400, 401, 404, 410)"""


# Default HTTP status code retry classifications
DEFAULT_HTTP_RETRY_MAP: dict[int, HTTPRetryBehavior] = {
    # Fully retriable: server errors and explicit rate limiting
    429: HTTPRetryBehavior.FULL,  # Too Many Requests
    500: HTTPRetryBehavior.FULL,  # Internal Server Error
    502: HTTPRetryBehavior.FULL,  # Bad Gateway
    503: HTTPRetryBehavior.FULL,  # Service Unavailable
    504: HTTPRetryBehavior.FULL,  # Gateway Timeout
    # Conservatively retriable: might be temporary
    403: HTTPRetryBehavior.CONSERVATIVE,  # Forbidden (could be rate limiting)
    408: HTTPRetryBehavior.CONSERVATIVE,  # Request Timeout
    # Never retriable: client errors
    400: HTTPRetryBehavior.NEVER,  # Bad Request
    401: HTTPRetryBehavior.NEVER,  # Unauthorized
    404: HTTPRetryBehavior.NEVER,  # Not Found
    405: HTTPRetryBehavior.NEVER,  # Method Not Allowed
    410: HTTPRetryBehavior.NEVER,  # Gone
    422: HTTPRetryBehavior.NEVER,  # Unprocessable Entity
}


class RetryException(RuntimeError):
    """
    Base exception class for retry-related errors.
    """


class RetryExhaustedException(RetryException):
    """
    Retries exhausted (this is not retriable).
    """

    def __init__(self, original_exception: Exception, max_retries: int, total_time: float):
        self.original_exception = original_exception
        self.max_retries = max_retries
        self.total_time = total_time

        super().__init__(
            f"Max retries ({max_retries}) exhausted after {total_time:.1f}s. "
            f"Final error: {type(original_exception).__name__}: {original_exception}"
        )


def default_is_retriable(exception: Exception) -> bool:
    """
    Default retriable exception checker with HTTP status code awareness.

    Args:
        exception: The exception to check

    Returns:
        True if the exception should be retried with backoff
    """
    # Check for LiteLLM specific exceptions first, as a soft dependency.
    try:
        import litellm.exceptions

        # Check for specific LiteLLM exception types
        if isinstance(
            exception,
            (
                litellm.exceptions.RateLimitError,
                litellm.exceptions.APIError,
            ),
        ):
            return True
    except ImportError:
        # LiteLLM not available, fall back to other detection methods
        pass

    # Try to extract HTTP status code for more precise handling
    status_code = extract_http_status_code(exception)
    if status_code is not None:
        return is_http_status_retriable(status_code, DEFAULT_HTTP_RETRY_MAP)

    # Fallback to string-based detection for transient errors
    exception_str = str(exception).lower()

    # Check exception type names for common transient network errors
    exception_type = type(exception).__name__.lower()

    transient_error_indicators = [
        # Rate limiting and quota errors
        "rate limit",
        "too many requests",
        "try again later",
        "429",
        "quota exceeded",
        "throttled",
        "rate_limit_error",
        "ratelimiterror",
        # Server errors
        "server error",
        "service unavailable",
        "bad gateway",
        "gateway timeout",
        "internal server error",
        "502",
        "503",
        "504",
        "500",
        # Network connectivity errors
        "connection timeout",
        "connection timed out",
        "read timeout",
        "timeout error",
        "timed out",
        "connection reset",
        "connection refused",
        "connection aborted",
        "connection error",
        "network error",
        "network unreachable",
        "network is unreachable",
        "no route to host",
        "temporary failure",
        "name resolution failed",
        "dns",
        "resolver",
        # SSL/TLS transient errors
        "ssl error",
        "certificate verify failed",
        "handshake timeout",
        # Common transient exception types
        "connectionerror",
        "timeouterror",
        "connecttimeout",
        "readtimeout",
        "httperror",
        "requestexception",
    ]

    # Check both exception message and type name
    return any(indicator in exception_str for indicator in transient_error_indicators) or any(
        indicator in exception_type for indicator in transient_error_indicators
    )


def is_http_status_retriable(
    status_code: int,
    retry_policy: dict[int, HTTPRetryBehavior] | None = None,
) -> bool:
    """
    Determine if an HTTP status code should be retried.

    Args:
        status_code: HTTP status code
        retry_policy: Custom retry behavior policy (uses default if None)

    Returns:
        True if the status code should be retried
    """
    if retry_policy is None:
        retry_policy = DEFAULT_HTTP_RETRY_MAP

    behavior = retry_policy.get(status_code)

    if behavior == HTTPRetryBehavior.FULL:
        return True
    elif behavior == HTTPRetryBehavior.CONSERVATIVE:
        return True  # Conservative retries are enabled by default
    elif behavior == HTTPRetryBehavior.NEVER:
        return False

    # Unknown status code: use heuristics
    if 500 <= status_code <= 599:
        # Server errors are generally retriable
        return True
    elif status_code == 429:
        # Rate limiting is always retriable
        return True
    elif 400 <= status_code <= 499:
        # Client errors are generally not retriable, except for specific cases
        return False

    # Default to not retriable for unknown codes
    return False


@dataclass(frozen=True)
class RetrySettings:
    """
    Retry behavior when handling concurrent requests.
    """

    max_task_retries: int
    """Maximum retries per individual task (0 = no retries)"""

    max_total_retries: int | None = None
    """Maximum retries across all tasks combined (None = no global limit)"""

    initial_backoff: float = 1.0
    """Base backoff time in seconds"""

    max_backoff: float = 128.0
    """Maximum backoff time in seconds"""

    backoff_factor: float = 2.0
    """Exponential backoff multiplier"""

    is_retriable: Callable[[Exception], bool] = default_is_retriable
    """Function to determine if non-HTTP exceptions should be retried (network errors, timeouts, etc.)"""

    http_retry_policy: dict[int, HTTPRetryBehavior] | None = None
    """Custom HTTP status code retry behavior policy (None = use defaults)"""

    def should_retry(self, exception: Exception) -> bool:
        """
        Determine if an exception should be retried.

        First checks for HTTP status codes and uses http_retry_policy if present.
        For non-HTTP exceptions, uses the is_retriable function to determine
        if other exception types (network errors, timeouts, etc.) should be retried.
        """
        # First check if this is an HTTP exception with a status code
        status_code = extract_http_status_code(exception)
        if status_code:
            retry_policy = (
                self.http_retry_policy
                if self.http_retry_policy is not None
                else DEFAULT_HTTP_RETRY_MAP
            )
            return is_http_status_retriable(status_code, retry_policy)

        # Not an HTTP error - use is_retriable for other exception types
        # (network errors, timeouts, connection issues, etc.)
        return self.is_retriable(exception)


DEFAULT_RETRIES = RetrySettings(
    max_task_retries=15,
    max_total_retries=1000,
    initial_backoff=1.0,
    max_backoff=60.0,
    backoff_factor=1.5,
    is_retriable=default_is_retriable,
)
"""Reasonable default retry settings with both per-task and global limits."""

# Conservative retry settings use a custom retry policy that excludes conservative retries
_CONSERVATIVE_HTTP_RETRY_POLICY = {
    # Fully retriable: server errors and explicit rate limiting
    429: HTTPRetryBehavior.FULL,
    500: HTTPRetryBehavior.FULL,
    502: HTTPRetryBehavior.FULL,
    503: HTTPRetryBehavior.FULL,
    504: HTTPRetryBehavior.FULL,
    # Conservative codes become NEVER for conservative mode
    403: HTTPRetryBehavior.NEVER,
    408: HTTPRetryBehavior.NEVER,
    # Never retriable: client errors
    400: HTTPRetryBehavior.NEVER,
    401: HTTPRetryBehavior.NEVER,
    404: HTTPRetryBehavior.NEVER,
    405: HTTPRetryBehavior.NEVER,
    410: HTTPRetryBehavior.NEVER,
    422: HTTPRetryBehavior.NEVER,
}

CONSERVATIVE_RETRIES = RetrySettings(
    max_task_retries=5,
    max_total_retries=50,
    initial_backoff=2.0,
    max_backoff=60.0,
    backoff_factor=2.5,
    http_retry_policy=_CONSERVATIVE_HTTP_RETRY_POLICY,
)
"""Conservative retry settings - fewer retries, longer backoff, no conservative HTTP retries."""


NO_RETRIES = RetrySettings(
    max_task_retries=0,
    max_total_retries=0,
    initial_backoff=0.0,
    max_backoff=0.0,
    backoff_factor=1.0,
    is_retriable=lambda _: False,
)
"""Disable retries completely."""


def extract_retry_after(exception: Exception) -> float | None:
    """
    Try to extract retry-after time from exception headers or message.

    Args:
        exception: The exception to extract retry-after from

    Returns:
        Retry-after time in seconds, or None if not found
    """
    # Check if exception has response headers
    response = getattr(exception, "response", None)
    if response:
        headers = getattr(response, "headers", None)
        if headers and "retry-after" in headers:
            try:
                return float(headers["retry-after"])
            except (ValueError, TypeError):
                pass

    # Check for retry_after attribute
    retry_after = getattr(exception, "retry_after", None)
    if retry_after is not None:
        try:
            return float(retry_after)
        except (ValueError, TypeError):
            pass

    return None


def calculate_backoff(
    attempt: int,
    exception: Exception,
    *,
    initial_backoff: float,
    max_backoff: float,
    backoff_factor: float,
) -> float:
    """
    Calculate backoff time using exponential backoff with jitter.

    Args:
        attempt: Current attempt number (0-based)
        exception: The exception that triggered the backoff
        initial_backoff: Base backoff time in seconds
        max_backoff: Maximum backoff time in seconds
        backoff_factor: Exponential backoff multiplier

    Returns:
        Backoff time in seconds
    """
    # Try to extract retry-after header if available
    retry_after = extract_retry_after(exception)
    if retry_after is not None:
        return min(retry_after, max_backoff)

    # Exponential backoff: initial_backoff * (backoff_factor ^ attempt)
    exponential_backoff = initial_backoff * (backoff_factor**attempt)

    # Add significant jitter (±50% randomization) to prevent thundering herd
    jitter_factor = 1 + (random.random() - 0.5) * 1.0
    backoff_with_jitter = exponential_backoff * jitter_factor
    # Add a small random base delay (0 to 50% of initial_backoff) to further spread out retries
    base_delay = random.random() * (initial_backoff * 0.5)
    total_backoff = backoff_with_jitter + base_delay

    return min(total_backoff, max_backoff)
