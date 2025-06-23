from __future__ import annotations

import asyncio
import inspect
import logging
from collections.abc import Callable, Coroutine
from typing import Any, TypeAlias, TypeVar, overload

from aiolimiter import AsyncLimiter

from kash.utils.api_utils.api_retries import (
    DEFAULT_RETRIES,
    NO_RETRIES,
    RetryExhaustedException,
    RetrySettings,
    calculate_backoff,
)
from kash.utils.api_utils.progress_protocol import Labeler, ProgressTracker, TaskState

T = TypeVar("T")

log = logging.getLogger(__name__)

# Type alias for coroutine specification
CoroSpec: TypeAlias = Callable[[], Coroutine[None, None, T]] | Coroutine[None, None, T]
# Type alias for sync function specification
SyncSpec: TypeAlias = Callable[[], T]

# Specific labeler types using the generic Labeler pattern
CoroLabeler: TypeAlias = Labeler[CoroSpec[T]]
SyncLabeler: TypeAlias = Labeler[SyncSpec[T]]

DEFAULT_MAX_CONCURRENT: int = 5
DEFAULT_MAX_RPS: float = 5.0


class RetryCounter:
    """Thread-safe counter for tracking retries across all tasks."""

    def __init__(self, max_total_retries: int | None):
        self.max_total_retries = max_total_retries
        self.count = 0
        self._lock = asyncio.Lock()

    async def try_increment(self) -> bool:
        """
        Try to increment the retry counter.
        Returns True if increment was successful, False if limit reached.
        """
        if self.max_total_retries is None:
            return True

        async with self._lock:
            if self.count < self.max_total_retries:
                self.count += 1
                return True
            return False


@overload
async def gather_limited(
    *coro_specs: CoroSpec[T],
    max_concurrent: int = DEFAULT_MAX_CONCURRENT,
    max_rps: float = DEFAULT_MAX_RPS,
    return_exceptions: bool = False,
    retry_settings: RetrySettings | None = DEFAULT_RETRIES,
    status: ProgressTracker | None = None,
    labeler: CoroLabeler[T] | None = None,
) -> list[T]: ...


@overload
async def gather_limited(
    *coro_specs: CoroSpec[T],
    max_concurrent: int = DEFAULT_MAX_CONCURRENT,
    max_rps: float = DEFAULT_MAX_RPS,
    return_exceptions: bool = True,
    retry_settings: RetrySettings | None = DEFAULT_RETRIES,
    status: ProgressTracker | None = None,
    labeler: CoroLabeler[T] | None = None,
) -> list[T | BaseException]: ...


async def gather_limited(
    *coro_specs: CoroSpec[T],
    max_concurrent: int = DEFAULT_MAX_CONCURRENT,
    max_rps: float = DEFAULT_MAX_RPS,
    return_exceptions: bool = False,
    retry_settings: RetrySettings | None = DEFAULT_RETRIES,
    status: ProgressTracker | None = None,
    labeler: CoroLabeler[T] | None = None,
) -> list[T] | list[T | BaseException]:
    """
    Rate-limited version of `asyncio.gather()` with retry logic and optional progress display.
    Uses the aiolimiter leaky-bucket algorithm with exponential backoff on failures.

    Supports two levels of retry limits:
    - Per-task retries: max_task_retries attempts per individual task
    - Global retries: max_total_retries attempts across all tasks (prevents cascade failures)

    Can optionally display live progress with retry indicators using TaskStatus.

    Accepts either:
    - Callables that return coroutines: `lambda: some_async_func(arg)` (recommended for retries)
    - Coroutines directly: `some_async_func(arg)` (only if retries disabled)

    Examples:
        ```python
        # With progress display and custom labeling:
        from kash.utils.rich_custom.task_status import TaskStatus

        async with TaskStatus() as status:
            await gather_limited(
                lambda: fetch_url("http://example.com"),
                lambda: process_data(data),
                status=status,
                labeler=lambda i, spec: f"Task {i+1}",
                retry_settings=RetrySettings(max_task_retries=3, max_total_retries=25)
            )

        # Without progress display:
        await gather_limited(
            lambda: fetch_url("http://example.com"),
            lambda: process_data(data),
            retry_settings=RetrySettings(max_task_retries=3, max_total_retries=25)
        )

        ```

    Args:
        *coro_specs: Callables or coroutines to execute
        max_concurrent: Maximum number of concurrent executions
        max_rps: Maximum requests per second
        return_exceptions: If True, exceptions are returned as results
        retry_settings: Configuration for retry behavior, or None to disable retries
        status: Optional ProgressTracker instance for progress display
        labeler: Optional function to generate labels: labeler(index, spec) -> str

    Returns:
        List of results in the same order as input specifications

    Raises:
        ValueError: If coroutines are passed when retries are enabled
    """
    log.info(
        "Executing with concurrency %s at %s rps, %s",
        max_concurrent,
        max_rps,
        retry_settings,
    )
    if not coro_specs:
        return []

    retry_settings = retry_settings or NO_RETRIES

    # Validate that coroutines aren't used when retries are enabled
    if retry_settings.max_task_retries > 0:
        for i, spec in enumerate(coro_specs):
            if inspect.iscoroutine(spec):
                raise ValueError(
                    f"Coroutine at position {i} cannot be retried. "
                    f"When retries are enabled (max_task_retries > 0), pass callables that return fresh coroutines: "
                    f"lambda: your_async_func(args) instead of your_async_func(args)"
                )

    semaphore = asyncio.Semaphore(max_concurrent)
    rate_limiter = AsyncLimiter(max_rps, 1.0)

    # Global retry counter (shared across all tasks)
    global_retry_counter = RetryCounter(retry_settings.max_total_retries)

    async def rate_limited_coro_with_retry(i: int, coro_spec: CoroSpec[T]) -> T:
        # Generate label for this task
        label = labeler(i, coro_spec) if labeler else f"task:{i}"
        task_id = await status.add(label) if status else None

        async def executor() -> T:
            # Create a fresh coroutine for each attempt
            if callable(coro_spec):
                coro = coro_spec()
            else:
                # Direct coroutine - only valid if retries disabled
                coro = coro_spec
            return await coro

        try:
            result = await _execute_with_retry(
                executor,
                retry_settings,
                semaphore,
                rate_limiter,
                global_retry_counter,
                status,
                task_id,
            )

            # Mark as completed successfully
            if status and task_id is not None:
                await status.finish(task_id, TaskState.COMPLETED)

            return result

        except Exception as e:
            # Mark as failed
            if status and task_id is not None:
                await status.finish(task_id, TaskState.FAILED, str(e))
            raise

    return await asyncio.gather(
        *[rate_limited_coro_with_retry(i, spec) for i, spec in enumerate(coro_specs)],
        return_exceptions=return_exceptions,
    )


@overload
async def gather_limited_sync(
    *sync_specs: SyncSpec[T],
    max_concurrent: int = DEFAULT_MAX_CONCURRENT,
    max_rps: float = DEFAULT_MAX_RPS,
    return_exceptions: bool = False,
    retry_settings: RetrySettings | None = DEFAULT_RETRIES,
    status: ProgressTracker | None = None,
    labeler: SyncLabeler[T] | None = None,
) -> list[T]: ...


@overload
async def gather_limited_sync(
    *sync_specs: SyncSpec[T],
    max_concurrent: int = DEFAULT_MAX_CONCURRENT,
    max_rps: float = DEFAULT_MAX_RPS,
    return_exceptions: bool = True,
    retry_settings: RetrySettings | None = DEFAULT_RETRIES,
    status: ProgressTracker | None = None,
    labeler: SyncLabeler[T] | None = None,
) -> list[T | BaseException]: ...


async def gather_limited_sync(
    *sync_specs: SyncSpec[T],
    max_concurrent: int = DEFAULT_MAX_CONCURRENT,
    max_rps: float = DEFAULT_MAX_RPS,
    return_exceptions: bool = False,
    retry_settings: RetrySettings | None = DEFAULT_RETRIES,
    status: ProgressTracker | None = None,
    labeler: SyncLabeler[T] | None = None,
) -> list[T] | list[T | BaseException]:
    """
    Rate-limited version of `asyncio.gather()` for sync functions with retry logic.
    Handles the asyncio.to_thread() boundary correctly for consistent exception propagation.

    Supports two levels of retry limits:
    - Per-task retries: max_task_retries attempts per individual task
    - Global retries: max_total_retries attempts across all tasks (prevents cascade failures)

    Args:
        *sync_specs: Callables that return values (not coroutines)
        max_concurrent: Maximum number of concurrent executions
        max_rps: Maximum requests per second
        return_exceptions: If True, exceptions are returned as results
        retry_settings: Configuration for retry behavior, or None to disable retries
        status: Optional ProgressTracker instance for progress display
        labeler: Optional function to generate labels: labeler(index, spec) -> str

    Returns:
        List of results in the same order as input specifications

    Example:
        ```python
        # Sync functions with retries
        results = await gather_limited_sync(
            lambda: some_sync_function(arg1),
            lambda: another_sync_function(arg2),
            max_concurrent=3,
            max_rps=2.0,
            retry_settings=RetrySettings(max_task_retries=3, max_total_retries=25)
        )
        ```
    """
    log.info(
        "Executing with concurrency %s at %s rps, %s",
        max_concurrent,
        max_rps,
        retry_settings,
    )
    if not sync_specs:
        return []

    retry_settings = retry_settings or NO_RETRIES

    semaphore = asyncio.Semaphore(max_concurrent)
    rate_limiter = AsyncLimiter(max_rps, 1.0)

    # Global retry counter (shared across all tasks)
    global_retry_counter = RetryCounter(retry_settings.max_total_retries)

    async def rate_limited_sync_with_retry(i: int, sync_spec: SyncSpec[T]) -> T:
        # Generate label for this task
        label = labeler(i, sync_spec) if labeler else f"sync_task:{i}"
        task_id = await status.add(label) if status else None

        async def executor() -> T:
            # Call sync function via asyncio.to_thread, handling retry at this level
            result = await asyncio.to_thread(sync_spec)
            # Check if the callable returned a coroutine (which would be a bug)
            if inspect.iscoroutine(result):
                # Clean up the coroutine we accidentally created
                result.close()
                raise ValueError(
                    "Callable returned a coroutine. "
                    "gather_limited_sync() is for synchronous functions only. "
                    "Use gather_limited() for async functions."
                )
            return result

        try:
            result = await _execute_with_retry(
                executor,
                retry_settings,
                semaphore,
                rate_limiter,
                global_retry_counter,
                status,
                task_id,
            )

            # Mark as completed successfully
            if status and task_id is not None:
                await status.finish(task_id, TaskState.COMPLETED)

            return result

        except Exception as e:
            # Mark as failed
            if status and task_id is not None:
                await status.finish(task_id, TaskState.FAILED, str(e))
            raise

    return await asyncio.gather(
        *[rate_limited_sync_with_retry(i, spec) for i, spec in enumerate(sync_specs)],
        return_exceptions=return_exceptions,
    )


async def _execute_with_retry(
    executor: Callable[[], Coroutine[None, None, T]],
    retry_settings: RetrySettings,
    semaphore: asyncio.Semaphore,
    rate_limiter: AsyncLimiter,
    global_retry_counter: RetryCounter,
    status: ProgressTracker | None = None,
    task_id: Any | None = None,
) -> T:
    import time

    start_time = time.time()
    last_exception: Exception | None = None

    for attempt in range(retry_settings.max_task_retries + 1):
        # Handle backoff before acquiring any resources
        if attempt > 0 and last_exception is not None:
            # Try to increment global retry counter
            if not await global_retry_counter.try_increment():
                log.error(
                    f"Global retry limit ({global_retry_counter.max_total_retries}) reached. "
                    f"Cannot retry task after: {type(last_exception).__name__}: {last_exception}"
                )
                raise last_exception

            backoff_time = calculate_backoff(
                attempt - 1,  # Previous attempt that failed
                last_exception,
                initial_backoff=retry_settings.initial_backoff,
                max_backoff=retry_settings.max_backoff,
                backoff_factor=retry_settings.backoff_factor,
            )

            # Record retry in status display and log appropriately
            if status and task_id is not None:
                # Include retry attempt info and backoff time in the status display
                retry_info = (
                    f"Attempt {attempt}/{retry_settings.max_task_retries} "
                    f"(waiting {backoff_time:.1f}s): {type(last_exception).__name__}: {last_exception}"
                )
                await status.update(task_id, error_msg=retry_info)

                # Use debug level for Rich trackers, warning/info for console trackers
                use_debug_level = status.suppress_logs
            else:
                # No status display: use full logging
                use_debug_level = False

            # Log retry information at appropriate level
            rate_limit_msg = (
                f"Rate limit hit (attempt {attempt}/{retry_settings.max_task_retries} "
                f"{global_retry_counter.count}/{global_retry_counter.max_total_retries or '∞'} total) "
                f"backing off for {backoff_time:.2f}s"
            )
            exception_msg = (
                f"Rate limit exception: {type(last_exception).__name__}: {last_exception}"
            )

            if use_debug_level:
                log.debug(rate_limit_msg)
                log.debug(exception_msg)
            else:
                log.warning(rate_limit_msg)
                log.info(exception_msg)
            await asyncio.sleep(backoff_time)

        try:
            # Acquire semaphore and rate limiter right before making the call
            async with semaphore, rate_limiter:
                return await executor()
        except Exception as e:
            last_exception = e  # Always store the exception

            if attempt == retry_settings.max_task_retries:
                # Final attempt failed
                if retry_settings.max_task_retries == 0:
                    # No retries configured - raise original exception directly
                    raise
                else:
                    # Retries were attempted but exhausted - wrap with context
                    total_time = time.time() - start_time
                    log.error(
                        f"Max task retries ({retry_settings.max_task_retries}) exhausted after {total_time:.1f}s. "
                        f"Final attempt failed with: {type(e).__name__}: {e}"
                    )
                    raise RetryExhaustedException(e, retry_settings.max_task_retries, total_time)

            # Check if this is a retriable exception
            if retry_settings.is_retriable(e):
                # Continue to next retry attempt (global limits will be checked at top of loop)
                continue
            else:
                # Non-retriable exception, log and re-raise immediately
                log.warning("Non-retriable exception (not retrying): %s", e, exc_info=True)
                raise

    # This should never be reached, but satisfy type checker
    raise RuntimeError("Unexpected code path in _execute_with_retry")


## Tests


def test_gather_limited_sync():
    """Test gather_limited_sync with sync functions."""
    import asyncio
    import time

    async def run_test():
        def sync_func(value: int) -> int:
            """Simple sync function for testing."""
            time.sleep(0.1)  # Simulate some work
            return value * 2

        # Test basic functionality
        results = await gather_limited_sync(
            lambda: sync_func(1),
            lambda: sync_func(2),
            lambda: sync_func(3),
            max_concurrent=2,
            max_rps=10.0,
            retry_settings=NO_RETRIES,
        )

        assert results == [2, 4, 6]

    # Run the async test
    asyncio.run(run_test())


def test_gather_limited_sync_with_retries():
    """Test that sync functions can be retried on retriable exceptions."""
    import asyncio

    async def run_test():
        call_count = 0

        def flaky_sync_func() -> str:
            """Sync function that fails first time, succeeds second time."""
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Rate limit exceeded")  # Retriable
            return "success"

        # Should succeed after retry
        results = await gather_limited_sync(
            lambda: flaky_sync_func(),
            retry_settings=RetrySettings(
                max_task_retries=2,
                initial_backoff=0.1,
                max_backoff=1.0,
                backoff_factor=2.0,
            ),
        )

        assert results == ["success"]
        assert call_count == 2  # Called twice (failed once, succeeded once)

    # Run the async test
    asyncio.run(run_test())


def test_gather_limited_async_basic():
    """Test gather_limited with async functions using callables."""
    import asyncio

    async def run_test():
        async def async_func(value: int) -> int:
            """Simple async function for testing."""
            await asyncio.sleep(0.05)  # Simulate async work
            return value * 3

        # Test with callables (recommended pattern)
        results = await gather_limited(
            lambda: async_func(1),
            lambda: async_func(2),
            lambda: async_func(3),
            max_concurrent=2,
            max_rps=10.0,
            retry_settings=NO_RETRIES,
        )

        assert results == [3, 6, 9]

    asyncio.run(run_test())


def test_gather_limited_direct_coroutines():
    """Test gather_limited with direct coroutines when retries disabled."""
    import asyncio

    async def run_test():
        async def async_func(value: int) -> int:
            await asyncio.sleep(0.05)
            return value * 4

        # Test with direct coroutines (only works when retries disabled)
        results = await gather_limited(
            async_func(1),
            async_func(2),
            async_func(3),
            retry_settings=NO_RETRIES,  # Required for direct coroutines
        )

        assert results == [4, 8, 12]

    asyncio.run(run_test())


def test_gather_limited_coroutine_retry_validation():
    """Test that passing coroutines with retries enabled raises ValueError."""
    import asyncio

    async def run_test():
        async def async_func(value: int) -> int:
            return value

        # Should raise ValueError when trying to use coroutines with retries
        try:
            await gather_limited(
                async_func(1),  # Direct coroutine
                lambda: async_func(2),  # Callable
                retry_settings=RetrySettings(
                    max_task_retries=1,
                    initial_backoff=0.1,
                    max_backoff=1.0,
                    backoff_factor=2.0,
                ),
            )
            raise AssertionError("Expected ValueError")
        except ValueError as e:
            assert "position 0" in str(e)
            assert "cannot be retried" in str(e)

    asyncio.run(run_test())


def test_gather_limited_async_with_retries():
    """Test that async functions can be retried when using callables."""
    import asyncio

    async def run_test():
        call_count = 0

        async def flaky_async_func() -> str:
            """Async function that fails first time, succeeds second time."""
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Rate limit exceeded")  # Retriable
            return "async_success"

        # Should succeed after retry using callable
        results = await gather_limited(
            lambda: flaky_async_func(),
            retry_settings=RetrySettings(
                max_task_retries=2,
                initial_backoff=0.1,
                max_backoff=1.0,
                backoff_factor=2.0,
            ),
        )

        assert results == ["async_success"]
        assert call_count == 2  # Called twice (failed once, succeeded once)

    asyncio.run(run_test())


def test_gather_limited_sync_coroutine_validation():
    """Test that passing async function callables to sync version raises ValueError."""
    import asyncio

    async def run_test():
        async def async_func(value: int) -> int:
            return value

        # Should raise ValueError when trying to use async functions in sync version
        try:
            await gather_limited_sync(
                lambda: async_func(1),  # Returns coroutine - should be rejected
                retry_settings=NO_RETRIES,
            )
            raise AssertionError("Expected ValueError")
        except ValueError as e:
            assert "returned a coroutine" in str(e)
            assert "gather_limited_sync() is for synchronous functions only" in str(e)

    asyncio.run(run_test())


def test_gather_limited_retry_exhaustion():
    """Test that retry exhaustion produces clear error messages."""
    import asyncio

    async def run_test():
        call_count = 0

        def always_fails() -> str:
            """Function that always raises retriable exceptions."""
            nonlocal call_count
            call_count += 1
            raise Exception("Rate limit exceeded")  # Always retriable

        # Should exhaust retries and raise RetryExhaustedException
        try:
            await gather_limited_sync(
                lambda: always_fails(),
                retry_settings=RetrySettings(
                    max_task_retries=2,
                    initial_backoff=0.01,
                    max_backoff=0.1,
                    backoff_factor=2.0,
                ),
            )
            raise AssertionError("Expected RetryExhaustedException")
        except RetryExhaustedException as e:
            assert "Max retries (2) exhausted" in str(e)
            assert "Rate limit exceeded" in str(e)
            assert isinstance(e.original_exception, Exception)
            assert call_count == 3  # Initial attempt + 2 retries

    asyncio.run(run_test())


def test_gather_limited_return_exceptions():
    """Test return_exceptions=True behavior for both functions."""
    import asyncio

    async def run_test():
        def failing_sync() -> str:
            raise ValueError("sync error")

        async def failing_async() -> str:
            raise ValueError("async error")

        # Test sync version with exceptions returned
        sync_results = await gather_limited_sync(
            lambda: "success",
            lambda: failing_sync(),
            return_exceptions=True,
            retry_settings=NO_RETRIES,
        )

        assert len(sync_results) == 2
        assert sync_results[0] == "success"
        assert isinstance(sync_results[1], ValueError)
        assert str(sync_results[1]) == "sync error"

        async def success_async() -> str:
            return "async_success"

        # Test async version with exceptions returned
        async_results = await gather_limited(
            lambda: success_async(),
            lambda: failing_async(),
            return_exceptions=True,
            retry_settings=NO_RETRIES,
        )

        assert len(async_results) == 2
        assert async_results[0] == "async_success"
        assert isinstance(async_results[1], ValueError)
        assert str(async_results[1]) == "async error"

    asyncio.run(run_test())


def test_gather_limited_global_retry_limit():
    """Test that global retry limits are enforced across all tasks."""
    import asyncio

    async def run_test():
        retry_counts = {"task1": 0, "task2": 0}

        def flaky_task(task_name: str) -> str:
            """Tasks that always fail but track retry counts."""
            retry_counts[task_name] += 1
            raise Exception(f"Rate limit exceeded in {task_name}")

        # Test with very low global retry limit
        try:
            await gather_limited_sync(
                lambda: flaky_task("task1"),
                lambda: flaky_task("task2"),
                retry_settings=RetrySettings(
                    max_task_retries=5,  # Each task could retry up to 5 times
                    max_total_retries=3,  # But only 3 total retries across all tasks
                    initial_backoff=0.01,
                    max_backoff=0.1,
                    backoff_factor=2.0,
                ),
                return_exceptions=True,
            )
        except Exception:
            pass  # Expected to fail due to rate limits

        # Verify that total retries across both tasks doesn't exceed global limit
        total_retries = (retry_counts["task1"] - 1) + (
            retry_counts["task2"] - 1
        )  # -1 for initial attempts
        assert total_retries <= 3, f"Total retries {total_retries} exceeded global limit of 3"

        # Verify that both tasks were attempted at least once
        assert retry_counts["task1"] >= 1
        assert retry_counts["task2"] >= 1

    asyncio.run(run_test())
