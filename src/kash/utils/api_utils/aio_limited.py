from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import TypeVar, overload

from aiolimiter import AsyncLimiter

T = TypeVar("T")


@overload
async def gather_limited(
    *coros: Coroutine[None, None, T],
    max_concurrent: int = 5,
    max_rps: float = 5.0,
    return_exceptions: bool = False,
) -> list[T]: ...


@overload
async def gather_limited(
    *coros: Coroutine[None, None, T],
    max_concurrent: int = 5,
    max_rps: float = 5.0,
    return_exceptions: bool = True,
) -> list[T | BaseException]: ...


async def gather_limited(
    *coros: Coroutine[None, None, T],
    max_concurrent: int = 5,
    max_rps: float = 5.0,
    return_exceptions: bool = False,
) -> list[T] | list[T | BaseException]:
    """
    Rate-limited version of asyncio.gather(). Uses the aiolimiter leaky-bucket algorithm.

    Args:
        *coros: Coroutines to execute
        max_concurrent: Maximum number of concurrent executions
        max_rps: Maximum requests per second
        return_exceptions: If True, exceptions are returned as results

    Returns:
        List of results in the same order as input coroutines
    """
    if not coros:
        return []

    semaphore = asyncio.Semaphore(max_concurrent)
    rate_limiter = AsyncLimiter(max_rps, 1.0)

    async def rate_limited_coro(coro: Coroutine[None, None, T]) -> T:
        async with semaphore:
            async with rate_limiter:
                return await coro

    return await asyncio.gather(
        *[rate_limited_coro(coro) for coro in coros], return_exceptions=return_exceptions
    )
