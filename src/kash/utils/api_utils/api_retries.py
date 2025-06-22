from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass


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
    Default retriable exception checker for common rate limit patterns.

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
        # LiteLLM not available, fall back to string-based detection
        pass

    # Fallback to string-based detection for general patterns
    exception_str = str(exception).lower()
    rate_limit_indicators = [
        "rate limit",
        "too many requests",
        "try again later",
        "429",
        "quota exceeded",
        "throttled",
        "rate_limit_error",
        "ratelimiterror",
    ]

    return any(indicator in exception_str for indicator in rate_limit_indicators)


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
    """Function to determine if an exception should be retried"""


DEFAULT_RETRIES = RetrySettings(
    max_task_retries=10,
    max_total_retries=100,
    initial_backoff=1.0,
    max_backoff=128.0,
    backoff_factor=2.0,
    is_retriable=default_is_retriable,
)
"""Reasonable default retry settings with both per-task and global limits."""


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


## Tests


def test_default_is_retriable():
    """Test string-based rate limit detection."""
    # Positive cases
    assert default_is_retriable(Exception("Rate limit exceeded"))
    assert default_is_retriable(Exception("Too many requests"))
    assert default_is_retriable(Exception("HTTP 429 error"))
    assert default_is_retriable(Exception("Quota exceeded"))
    assert default_is_retriable(Exception("throttled"))
    assert default_is_retriable(Exception("RateLimitError"))

    # Negative cases
    assert not default_is_retriable(Exception("Authentication failed"))
    assert not default_is_retriable(Exception("Invalid API key"))
    assert not default_is_retriable(Exception("Network error"))


def test_default_is_retriable_litellm():
    """Test LiteLLM exception detection if available."""
    try:
        import litellm.exceptions

        # Test retriable LiteLLM exceptions
        rate_error = litellm.exceptions.RateLimitError(
            message="Rate limit", model="test", llm_provider="test"
        )
        api_error = litellm.exceptions.APIError(
            message="API error", model="test", llm_provider="test", status_code=500
        )
        assert default_is_retriable(rate_error)
        assert default_is_retriable(api_error)

        # Test non-retriable exception
        auth_error = litellm.exceptions.AuthenticationError(
            message="Auth failed", model="test", llm_provider="test"
        )
        assert not default_is_retriable(auth_error)

    except ImportError:
        # LiteLLM not available, skip
        pass


def test_extract_retry_after():
    """Test retry-after header extraction."""

    class MockResponse:
        def __init__(self, headers):
            self.headers = headers

    class MockException(Exception):
        def __init__(self, response=None, retry_after=None):
            self.response = response
            if retry_after is not None:
                self.retry_after = retry_after
            super().__init__()

    # Test response header
    response = MockResponse({"retry-after": "30"})
    assert extract_retry_after(MockException(response=response)) == 30.0

    # Test retry_after attribute
    assert extract_retry_after(MockException(retry_after=45.0)) == 45.0

    # Test no retry info
    assert extract_retry_after(MockException()) is None

    # Test invalid values
    invalid_response = MockResponse({"retry-after": "invalid"})
    assert extract_retry_after(MockException(response=invalid_response)) is None


def test_calculate_backoff():
    """Test backoff calculation."""

    class MockException(Exception):
        def __init__(self, retry_after=None):
            self.retry_after = retry_after
            super().__init__()

    # Test with retry_after header
    exception = MockException(retry_after=30.0)
    assert (
        calculate_backoff(
            attempt=1,
            exception=exception,
            initial_backoff=1.0,
            max_backoff=60.0,
            backoff_factor=2.0,
        )
        == 30.0
    )

    # Test exponential backoff with increased jitter and base delay
    exception = MockException()
    backoff = calculate_backoff(
        attempt=1,
        exception=exception,
        initial_backoff=1.0,
        max_backoff=60.0,
        backoff_factor=2.0,
    )
    # 2.0 base * (±50% jitter) + (0-50% of initial_backoff) = range ~1.0 to 3.5
    assert 1.0 <= backoff <= 3.5

    # Test max_backoff cap
    high_backoff = calculate_backoff(
        attempt=10,
        exception=exception,
        initial_backoff=1.0,
        max_backoff=5.0,
        backoff_factor=2.0,
    )
    assert high_backoff <= 5.0
