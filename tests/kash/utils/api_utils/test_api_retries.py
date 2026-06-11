"""Tests for api_retries: HTTP status extraction, retry classification, and backoff."""

from kash.utils.api_utils.api_retries import (
    _CONSERVATIVE_HTTP_RETRY_POLICY,
    CONSERVATIVE_RETRIES,
    RetrySettings,
    calculate_backoff,
    default_is_retriable,
    extract_http_status_code,
    extract_retry_after,
    is_http_status_retriable,
)


def test_extract_http_status_code():
    """Test HTTP status code extraction from various exception types."""

    class MockHTTPXResponse:
        def __init__(self, status_code):
            self.status_code = status_code

    class MockHTTPXException(Exception):
        def __init__(self, status_code):
            self.response = MockHTTPXResponse(status_code)
            super().__init__(f"HTTP {status_code} error")

    class MockAioHTTPException(Exception):
        def __init__(self, status):
            self.status = status
            super().__init__(f"HTTP {status} error")

    # Test httpx-style exceptions
    assert extract_http_status_code(MockHTTPXException(403)) == 403
    assert extract_http_status_code(MockHTTPXException(429)) == 429

    # Test aiohttp-style exceptions
    assert extract_http_status_code(MockAioHTTPException(500)) == 500

    # Test string parsing fallback
    assert extract_http_status_code(Exception("Client error '403 Forbidden'")) == 403
    assert extract_http_status_code(Exception("HTTP 429 Too Many Requests")) == 429
    assert extract_http_status_code(Exception("500 error occurred")) == 500

    # Test no status code
    assert extract_http_status_code(Exception("Network error")) is None


def test_is_http_status_retriable():
    """Test HTTP status code retry logic."""

    # Fully retriable
    assert is_http_status_retriable(429)  # Too Many Requests
    assert is_http_status_retriable(500)  # Internal Server Error
    assert is_http_status_retriable(502)  # Bad Gateway
    assert is_http_status_retriable(503)  # Service Unavailable
    assert is_http_status_retriable(504)  # Gateway Timeout

    # Conservative retriable (enabled by default)
    assert is_http_status_retriable(403)  # Forbidden
    assert is_http_status_retriable(408)  # Request Timeout

    # Conservative retriable with custom conservative policy (disabled)
    assert not is_http_status_retriable(403, _CONSERVATIVE_HTTP_RETRY_POLICY)
    assert not is_http_status_retriable(408, _CONSERVATIVE_HTTP_RETRY_POLICY)

    # Never retriable
    assert not is_http_status_retriable(400)  # Bad Request
    assert not is_http_status_retriable(401)  # Unauthorized
    assert not is_http_status_retriable(404)  # Not Found
    assert not is_http_status_retriable(410)  # Gone

    # Unknown status codes - use heuristics
    assert is_http_status_retriable(599)  # Unknown 5xx - retriable
    assert not is_http_status_retriable(499)  # Unknown 4xx - not retriable
    assert not is_http_status_retriable(299)  # Unknown 2xx - not retriable


def test_default_is_retriable_with_http():
    """Test enhanced default_is_retriable with HTTP status code awareness."""

    class MockHTTPXResponse:
        def __init__(self, status_code):
            self.status_code = status_code

    class MockHTTPXException(Exception):
        def __init__(self, status_code):
            self.response = MockHTTPXResponse(status_code)
            super().__init__(f"HTTP {status_code} error")

    # Test HTTP exceptions with known status codes
    assert default_is_retriable(MockHTTPXException(429))  # Rate limit - retriable
    assert default_is_retriable(MockHTTPXException(500))  # Server error - retriable
    assert default_is_retriable(MockHTTPXException(403))  # Conditional - retriable by default
    assert not default_is_retriable(MockHTTPXException(404))  # Not found - not retriable
    assert not default_is_retriable(MockHTTPXException(401))  # Unauthorized - not retriable

    # Test string-based fallback still works
    assert default_is_retriable(Exception("Rate limit exceeded"))
    assert default_is_retriable(Exception("503 Service Unavailable"))
    assert not default_is_retriable(Exception("Authentication failed"))


def test_default_is_retriable():
    """Test string-based transient error detection."""
    # Rate limiting cases
    assert default_is_retriable(Exception("Rate limit exceeded"))
    assert default_is_retriable(Exception("Too many requests"))
    assert default_is_retriable(Exception("HTTP 429 error"))
    assert default_is_retriable(Exception("Quota exceeded"))
    assert default_is_retriable(Exception("throttled"))
    assert default_is_retriable(Exception("RateLimitError"))

    # Network connectivity cases
    assert default_is_retriable(Exception("Network error"))
    assert default_is_retriable(Exception("Connection timeout"))
    assert default_is_retriable(Exception("Connection timed out"))
    assert default_is_retriable(Exception("Connection refused"))
    assert default_is_retriable(Exception("Network unreachable"))
    assert default_is_retriable(Exception("DNS resolution failed"))
    assert default_is_retriable(Exception("SSL error"))

    # Exception type-based detection
    class ConnectionError(Exception):
        pass

    class TimeoutError(Exception):
        pass

    assert default_is_retriable(ConnectionError("Some connection issue"))
    assert default_is_retriable(TimeoutError("Operation timed out"))

    # Non-retriable cases
    assert not default_is_retriable(Exception("Authentication failed"))
    assert not default_is_retriable(Exception("Invalid API key"))
    assert not default_is_retriable(Exception("Permission denied"))
    assert not default_is_retriable(Exception("File not found"))


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
    # base factor * (±50% jitter) + (0-50% of initial_backoff) = range calculation
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


def test_retry_settings_should_retry():
    """Test RetrySettings.should_retry method with custom HTTP maps."""

    class MockHTTPXResponse:
        def __init__(self, status_code):
            self.status_code = status_code

    class MockHTTPXException(Exception):
        def __init__(self, status_code):
            self.response = MockHTTPXResponse(status_code)
            super().__init__(f"HTTP {status_code} error")

    # Test with default settings (conservative retries enabled)
    default_settings = RetrySettings(max_task_retries=3)
    assert default_settings.should_retry(MockHTTPXException(429))  # Rate limit - retriable
    assert default_settings.should_retry(MockHTTPXException(500))  # Server error - retriable
    assert default_settings.should_retry(
        MockHTTPXException(403)
    )  # Conservative - retriable by default
    assert not default_settings.should_retry(MockHTTPXException(404))  # Not found - not retriable

    # Test with conservative settings (conservative retries disabled)
    conservative_settings = CONSERVATIVE_RETRIES
    assert conservative_settings.should_retry(
        MockHTTPXException(429)
    )  # Rate limit - still retriable
    assert conservative_settings.should_retry(
        MockHTTPXException(500)
    )  # Server error - still retriable
    assert not conservative_settings.should_retry(
        MockHTTPXException(403)
    )  # Conservative - now not retriable
    assert not conservative_settings.should_retry(
        MockHTTPXException(404)
    )  # Not found - still not retriable

    # Test with non-HTTP exception
    assert default_settings.should_retry(Exception("Network error"))
    assert not default_settings.should_retry(Exception("Authentication failed"))
