from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass


def default_is_retriable(exception: Exception) -> bool:
    """
    Default retriable exception checker for common rate limit patterns.

    Args:
        exception: The exception to check

    Returns:
        True if the exception should be retried with backoff
    """
    # Check for LiteLLM specific exceptions first
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
        "429",
        "quota exceeded",
        "throttled",
        "rate_limit_error",
        "ratelimiterror",
    ]

    return any(indicator in exception_str for indicator in rate_limit_indicators)


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

    # Add jitter (±25% randomization)
    jitter_factor = 1 + (random.random() - 0.5) * 0.5
    backoff_with_jitter = exponential_backoff * jitter_factor

    return min(backoff_with_jitter, max_backoff)


@dataclass(frozen=True)
class RetrySettings:
    """
    Configuration for retry behavior in rate-limited operations.
    """

    max_retries: int
    initial_backoff: float
    max_backoff: float
    backoff_factor: float = 2.0
    is_retriable: Callable[[Exception], bool] = default_is_retriable


DEFAULT_RETRY_SETTINGS = RetrySettings(
    max_retries=3,
    initial_backoff=1.0,
    max_backoff=60.0,
    backoff_factor=2.0,
    is_retriable=default_is_retriable,
)
"""Reasonable default retry settings."""


## Tests


def test_default_is_retriable_string_patterns():
    """Test string-based rate limit detection."""
    # Test positive cases
    assert default_is_retriable(Exception("Rate limit exceeded"))
    assert default_is_retriable(Exception("Too many requests"))
    assert default_is_retriable(Exception("HTTP 429 error"))
    assert default_is_retriable(Exception("Quota exceeded for your organization"))
    assert default_is_retriable(Exception("Request throttled"))
    assert default_is_retriable(Exception("rate_limit_error occurred"))
    assert default_is_retriable(Exception("RateLimitError: something went wrong"))

    # Test negative cases
    assert not default_is_retriable(Exception("Authentication failed"))
    assert not default_is_retriable(Exception("Invalid API key"))
    assert not default_is_retriable(Exception("Network connection error"))


def test_default_is_retriable_with_litellm():
    """Test LiteLLM exception detection when available."""
    try:
        import litellm.exceptions

        # Test LiteLLM specific exceptions
        rate_limit_error = litellm.exceptions.RateLimitError(
            message="Rate limit exceeded",
            model="test-model",
            llm_provider="test-provider",
        )
        assert default_is_retriable(rate_limit_error)

        api_error = litellm.exceptions.APIError(
            message="API error occurred",
            model="test-model",
            llm_provider="test-provider",
            status_code=500,
        )
        assert default_is_retriable(api_error)

        # Test non-retriable LiteLLM exception
        auth_error = litellm.exceptions.AuthenticationError(
            message="Authentication failed",
            model="test-model",
            llm_provider="test-provider",
        )
        assert not default_is_retriable(auth_error)

    except ImportError:
        # LiteLLM not available, skip this test
        pass


def test_calculate_backoff_with_retry_after():
    """Test backoff calculation with retry-after header."""

    # Mock exception with retry_after attribute
    class MockException(Exception):
        def __init__(self, retry_after=None):
            self.retry_after = retry_after
            super().__init__("Mock exception")

    # Test with retry_after
    exception_with_retry = MockException(retry_after=30.0)
    backoff = calculate_backoff(
        attempt=1,
        exception=exception_with_retry,
        initial_backoff=1.0,
        max_backoff=60.0,
        backoff_factor=2.0,
    )
    assert backoff == 30.0

    # Test without retry_after (should use exponential backoff)
    exception_without_retry = MockException()
    backoff = calculate_backoff(
        attempt=1,
        exception=exception_without_retry,
        initial_backoff=1.0,
        max_backoff=60.0,
        backoff_factor=2.0,
    )
    # Should be around 2.0 * jitter_factor (between 1.5 and 2.5)
    assert 1.5 <= backoff <= 2.5
