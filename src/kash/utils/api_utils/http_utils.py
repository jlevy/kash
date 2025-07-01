from __future__ import annotations


def extract_http_status_code(exception: Exception) -> int | None:
    """
    Extract HTTP status code from various exception types.

    Args:
        exception: The exception to extract status code from

    Returns:
        HTTP status code or None if not found
    """
    # Check for httpx.HTTPStatusError and requests.HTTPError
    if hasattr(exception, "response"):
        response = getattr(exception, "response", None)
        if response and hasattr(response, "status_code"):
            return getattr(response, "status_code", None)

    # Check for aiohttp errors
    if hasattr(exception, "status"):
        return getattr(exception, "status", None)

    # Parse from exception message as fallback
    exception_str = str(exception)

    # Try to find status code patterns in the message
    import re

    # Pattern for "403 Forbidden", "HTTP 429", etc.
    status_patterns = [
        r"\b(\d{3})\s+(?:Forbidden|Unauthorized|Not Found|Too Many Requests|Internal Server Error|Bad Gateway|Service Unavailable|Gateway Timeout)\b",
        r"\bHTTP\s+(\d{3})\b",
        r"\b(\d{3})\s+error\b",
        r"status\s*(?:code)?:\s*(\d{3})\b",
    ]

    for pattern in status_patterns:
        match = re.search(pattern, exception_str, re.IGNORECASE)
        if match:
            try:
                return int(match.group(1))
            except (ValueError, IndexError):
                continue

    return None
