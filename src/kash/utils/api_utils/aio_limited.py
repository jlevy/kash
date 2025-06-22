from __future__ import annotations

import asyncio
import logging
from collections.abc import Coroutine
from typing import TypeVar, overload

from aiolimiter import AsyncLimiter

from kash.utils.api_utils.api_retries import (
    DEFAULT_RETRY_SETTINGS,
    RetrySettings,
    calculate_backoff,
)

T = TypeVar("T")

log = logging.getLogger(__name__)


@overload
async def gather_limited(
    *coros: Coroutine[None, None, T],
    max_concurrent: int = 5,
    max_rps: float = 5.0,
    return_exceptions: bool = False,
    retry_settings: RetrySettings = DEFAULT_RETRY_SETTINGS,
) -> list[T]: ...


@overload
async def gather_limited(
    *coros: Coroutine[None, None, T],
    max_concurrent: int = 5,
    max_rps: float = 5.0,
    return_exceptions: bool = True,
    retry_settings: RetrySettings = DEFAULT_RETRY_SETTINGS,
) -> list[T | BaseException]: ...


async def gather_limited(
    *coros: Coroutine[None, None, T],
    max_concurrent: int = 5,
    max_rps: float = 5.0,
    return_exceptions: bool = False,
    retry_settings: RetrySettings = DEFAULT_RETRY_SETTINGS,
) -> list[T] | list[T | BaseException]:
    """
    Rate-limited version of `asyncio.gather()` with retry logic for rate limit exceptions.
    Uses the aiolimiter leaky-bucket algorithm with exponential backoff on failures.

    Args:
        *coros: Coroutines to execute
        max_concurrent: Maximum number of concurrent executions
        max_rps: Maximum requests per second
        return_exceptions: If True, exceptions are returned as results
        retry_settings: Configuration for retry behavior

    Returns:
        List of results in the same order as input coroutines
    """
    if not coros:
        return []

    semaphore = asyncio.Semaphore(max_concurrent)
    rate_limiter = AsyncLimiter(max_rps, 1.0)

    async def rate_limited_coro_with_retry(coro: Coroutine[None, None, T]) -> T:
        async with semaphore:
            for attempt in range(retry_settings.max_retries + 1):
                try:
                    async with rate_limiter:
                        return await coro
                except Exception as e:
                    if attempt == retry_settings.max_retries:
                        # Last attempt, re-raise the exception
                        raise

                    # Check if this is a retriable exception
                    if retry_settings.is_retriable(e):
                        backoff_time = calculate_backoff(
                            attempt,
                            e,
                            initial_backoff=retry_settings.initial_backoff,
                            max_backoff=retry_settings.max_backoff,
                            backoff_factor=retry_settings.backoff_factor,
                        )
                        log.debug(
                            f"Rate limit hit (attempt {attempt + 1}/{retry_settings.max_retries + 1}), "
                            f"backing off for {backoff_time:.2f}s: {type(e).__name__}"
                        )
                        await asyncio.sleep(backoff_time)
                        continue
                    else:
                        # Non-retriable exception, re-raise immediately
                        raise

        # This should never be reached, but satisfy type checker
        raise RuntimeError("Unexpected code path in rate_limited_coro_with_retry")

    return await asyncio.gather(
        *[rate_limited_coro_with_retry(coro) for coro in coros],
        return_exceptions=return_exceptions,
    )
