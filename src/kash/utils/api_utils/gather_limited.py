from __future__ import annotations

import asyncio
import inspect
import logging
import threading
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any, TypeAlias, TypeVar, cast, overload

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


@dataclass(frozen=True)
class FuncTask:
    """
    A task described as an unevaluated function with args and kwargs.
    This task format allows you to use args and kwargs in the Labeler.
    """

    func: Callable[..., Any]
    args: tuple[Any, ...] = ()
    kwargs: dict[str, Any] = field(default_factory=dict)


# Type aliases for coroutine and sync specifications, including unevaluated function specs
CoroSpec: TypeAlias = Callable[[], Coroutine[None, None, T]] | Coroutine[None, None, T] | FuncTask
SyncSpec: TypeAlias = Callable[[], T] | FuncTask

# Specific labeler types using the generic Labeler pattern
CoroLabeler: TypeAlias = Labeler[CoroSpec[T]]
SyncLabeler: TypeAlias = Labeler[SyncSpec[T]]

DEFAULT_MAX_CONCURRENT: int = 5
DEFAULT_MAX_RPS: float = 5.0
DEFAULT_CANCEL_TIMEOUT: float = 1.0


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
async def gather_limited_async(
    *coro_specs: CoroSpec[T],
    max_concurrent: int = DEFAULT_MAX_CONCURRENT,
    max_rps: float = DEFAULT_MAX_RPS,
    return_exceptions: bool = False,
    retry_settings: RetrySettings | None = DEFAULT_RETRIES,
    status: ProgressTracker | None = None,
    labeler: CoroLabeler[T] | None = None,
) -> list[T]: ...


@overload
async def gather_limited_async(
    *coro_specs: CoroSpec[T],
    max_concurrent: int = DEFAULT_MAX_CONCURRENT,
    max_rps: float = DEFAULT_MAX_RPS,
    return_exceptions: bool = True,
    retry_settings: RetrySettings | None = DEFAULT_RETRIES,
    status: ProgressTracker | None = None,
    labeler: CoroLabeler[T] | None = None,
) -> list[T | BaseException]: ...


async def gather_limited_async(
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

    Accepts:
    - Callables that return coroutines: `lambda: some_async_func(arg)` (recommended for retries)
    - Coroutines directly: `some_async_func(arg)` (only if retries disabled)
    - FuncSpec objects: `FuncSpec(some_async_func, (arg1, arg2), {"kwarg": value})` (args accessible to labeler)

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

    async def run_task_with_retry(i: int, coro_spec: CoroSpec[T]) -> T:
        # Generate label for this task
        label = labeler(i, coro_spec) if labeler else f"task:{i}"
        task_id = await status.add(label) if status else None

        async def executor() -> T:
            # Create a fresh coroutine for each attempt
            if isinstance(coro_spec, FuncTask):
                # FuncSpec format: FuncSpec(func, args, kwargs)
                coro = coro_spec.func(*coro_spec.args, **coro_spec.kwargs)
            elif callable(coro_spec):
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

    return await _gather_with_interrupt_handling(
        [run_task_with_retry(i, spec) for i, spec in enumerate(coro_specs)],
        return_exceptions,
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
    cancel_event: threading.Event | None = None,
    cancel_timeout: float = DEFAULT_CANCEL_TIMEOUT,
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
    cancel_event: threading.Event | None = None,
    cancel_timeout: float = DEFAULT_CANCEL_TIMEOUT,
) -> list[T | BaseException]: ...


async def gather_limited_sync(
    *sync_specs: SyncSpec[T],
    max_concurrent: int = DEFAULT_MAX_CONCURRENT,
    max_rps: float = DEFAULT_MAX_RPS,
    return_exceptions: bool = False,
    retry_settings: RetrySettings | None = DEFAULT_RETRIES,
    status: ProgressTracker | None = None,
    labeler: SyncLabeler[T] | None = None,
    cancel_event: threading.Event | None = None,
    cancel_timeout: float = DEFAULT_CANCEL_TIMEOUT,
) -> list[T] | list[T | BaseException]:
    """
    Rate-limited version of `asyncio.gather()` for sync functions with retry logic.
    Handles the asyncio.to_thread() boundary correctly for consistent exception propagation.

    Supports two levels of retry limits:
    - Per-task retries: max_task_retries attempts per individual task
    - Global retries: max_total_retries attempts across all tasks

    Supports cooperative cancellation and graceful thread termination on interruption.

    Args:
        *sync_specs: Callables that return values (not coroutines) or FuncTask objects
        max_concurrent: Maximum number of concurrent executions
        max_rps: Maximum requests per second
        return_exceptions: If True, exceptions are returned as results
        retry_settings: Configuration for retry behavior, or None to disable retries
        status: Optional ProgressTracker instance for progress display
        labeler: Optional function to generate labels: labeler(index, spec) -> str
        cancel_event: Optional threading.Event that will be set on cancellation
        cancel_timeout: Max seconds to wait for threads to terminate on cancellation

    Returns:
        List of results in the same order as input specifications

    Example:
        ```python
        # Without cooperative cancellation
        results = await gather_limited_sync(
            lambda: some_sync_function(arg1),
            lambda: another_sync_function(arg2),
            max_concurrent=3,
            max_rps=2.0,
            retry_settings=RetrySettings(max_task_retries=3, max_total_retries=25)
        )

        # With cooperative cancellation
        cancel_event = threading.Event()
        results = await gather_limited_sync(
            lambda: cancellable_sync_function(cancel_event, arg1),
            lambda: another_cancellable_function(cancel_event, arg2),
            cancel_event=cancel_event,
            cancel_timeout=5.0,
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

    async def run_task_with_retry(i: int, sync_spec: SyncSpec[T]) -> T:
        # Generate label for this task
        label = labeler(i, sync_spec) if labeler else f"task:{i}"
        task_id = await status.add(label) if status else None

        async def executor() -> T:
            # Call sync function via asyncio.to_thread, handling retry at this level
            if isinstance(sync_spec, FuncTask):
                # FuncSpec format: FuncSpec(func, args, kwargs)
                result = await asyncio.to_thread(
                    sync_spec.func, *sync_spec.args, **sync_spec.kwargs
                )
            else:
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
            return cast(T, result)

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

    return await _gather_with_interrupt_handling(
        [run_task_with_retry(i, spec) for i, spec in enumerate(sync_specs)],
        return_exceptions,
        cancel_event=cancel_event,
        cancel_timeout=cancel_timeout,
    )


async def _gather_with_interrupt_handling(
    tasks: list[Coroutine[None, None, T]],
    return_exceptions: bool = False,
    cancel_event: threading.Event | None = None,
    cancel_timeout: float = DEFAULT_CANCEL_TIMEOUT,
) -> list[T] | list[T | BaseException]:
    """
    Execute asyncio.gather with graceful KeyboardInterrupt handling.

    Args:
        tasks: List of coroutine functions to create tasks from
        return_exceptions: Whether to return exceptions as results
        cancel_event: Optional threading.Event to signal cancellation to sync functions
        cancel_timeout: Max seconds to wait for threads to terminate on cancellation

    Returns:
        Results from asyncio.gather

    Raises:
        KeyboardInterrupt: Re-raised after graceful cancellation
    """
    # Create tasks from coroutines so we can cancel them properly
    async_tasks = [asyncio.create_task(task) for task in tasks]

    try:
        return await asyncio.gather(*async_tasks, return_exceptions=return_exceptions)
    except (KeyboardInterrupt, asyncio.CancelledError) as e:
        # Handle both KeyboardInterrupt and CancelledError (which is what tasks actually receive)
        log.warning("Interrupt received, cancelling %d tasks...", len(async_tasks))

        # Signal cancellation to sync functions if event provided
        if cancel_event is not None:
            cancel_event.set()
            log.debug("Cancellation event set for cooperative sync function termination")

        # Cancel all running tasks
        cancelled_count = 0
        for task in async_tasks:
            if not task.done():
                task.cancel()
                cancelled_count += 1

        # Wait briefly for tasks to cancel
        if cancelled_count > 0:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*async_tasks, return_exceptions=True), timeout=cancel_timeout
                )
            except (TimeoutError, asyncio.CancelledError):
                log.warning("Some tasks did not cancel within timeout")

        # Wait for threads to terminate gracefully
        loop = asyncio.get_running_loop()
        try:
            log.debug("Waiting up to %.1fs for thread pool termination...", cancel_timeout)
            await asyncio.wait_for(
                loop.shutdown_default_executor(),
                timeout=cancel_timeout,
            )
            log.info("Thread pool shutdown completed")
        except TimeoutError:
            log.warning(
                "Thread pool shutdown timed out after %.1fs: some sync functions may still be running",
                cancel_timeout,
            )

        log.info("Task cancellation completed (%d tasks cancelled)", cancelled_count)
        # Always raise KeyboardInterrupt for consistent behavior
        raise KeyboardInterrupt("User cancellation") from e


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
                # Mark task as started now that we've passed rate limiting
                if status and task_id is not None and attempt == 0:
                    await status.start(task_id)
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
        results = await gather_limited_async(
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
        results = await gather_limited_async(
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

        coro = async_func(1)  # Direct coroutine

        # Should raise ValueError when trying to use coroutines with retries
        try:
            await gather_limited_async(
                coro,  # Direct coroutine
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
            coro.close()  # Close the unused coroutine to prevent RuntimeWarning
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
        results = await gather_limited_async(
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
        async_results = await gather_limited_async(
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


def test_gather_limited_funcspec_format():
    """Test gather_limited with FuncSpec format and custom labeler accessing args."""
    import asyncio

    async def run_test():
        def sync_func(name: str, value: int, multiplier: int = 2) -> str:
            """Sync function that takes args and kwargs."""
            return f"{name}: {value * multiplier}"

        async def async_func(name: str, value: int, multiplier: int = 2) -> str:
            """Async function that takes args and kwargs."""
            await asyncio.sleep(0.01)
            return f"{name}: {value * multiplier}"

        captured_labels = []

        def custom_labeler(i: int, spec: Any) -> str:
            if isinstance(spec, FuncTask):
                # Extract meaningful info from args for labeling
                if spec.args and len(spec.args) > 0:
                    label = f"Processing {spec.args[0]}"
                else:
                    label = f"Task {i}"
            else:
                label = f"Task {i}"
            captured_labels.append(label)
            return label

        # Test sync version with FuncSpec format and custom labeler
        sync_results = await gather_limited_sync(
            FuncTask(sync_func, ("user1", 100), {"multiplier": 3}),  # user1: 300
            FuncTask(sync_func, ("user2", 50)),  # user2: 100 (default multiplier)
            labeler=custom_labeler,
            retry_settings=NO_RETRIES,
        )

        assert sync_results == ["user1: 300", "user2: 100"]
        assert captured_labels == ["Processing user1", "Processing user2"]

        # Reset labels for async test
        captured_labels.clear()

        # Test async version with FuncSpec format and custom labeler
        async_results = await gather_limited_async(
            FuncTask(async_func, ("api_call", 10), {"multiplier": 4}),  # api_call: 40
            FuncTask(async_func, ("data_fetch", 5)),  # data_fetch: 10 (default multiplier)
            labeler=custom_labeler,
            retry_settings=NO_RETRIES,
        )

        assert async_results == ["api_call: 40", "data_fetch: 10"]
        assert captured_labels == ["Processing api_call", "Processing data_fetch"]

    asyncio.run(run_test())


def test_gather_limited_sync_cooperative_cancellation():
    """Test gather_limited_sync with cooperative cancellation via threading.Event."""
    import asyncio
    import time

    async def run_test():
        cancel_event = threading.Event()
        call_counts = {"task1": 0, "task2": 0}

        def cancellable_sync_func(task_name: str, work_duration: float) -> str:
            """Sync function that checks cancellation event periodically."""
            call_counts[task_name] += 1
            start_time = time.time()

            while time.time() - start_time < work_duration:
                if cancel_event.is_set():
                    return f"{task_name}: cancelled"
                time.sleep(0.01)  # Small sleep to allow cancellation check

            return f"{task_name}: completed"

        # Test cooperative cancellation - tasks should respect the cancel_event
        results = await gather_limited_sync(
            lambda: cancellable_sync_func("task1", 0.1),  # Short duration
            lambda: cancellable_sync_func("task2", 0.1),  # Short duration
            cancel_event=cancel_event,
            cancel_timeout=1.0,
            retry_settings=NO_RETRIES,
        )

        # Should complete normally since cancel_event wasn't set
        assert results == ["task1: completed", "task2: completed"]
        assert call_counts["task1"] == 1
        assert call_counts["task2"] == 1

        # Test that cancel_event can be used independently
        cancel_event.set()  # Set cancellation signal

        results2 = await gather_limited_sync(
            lambda: cancellable_sync_func("task1", 1.0),  # Would take long if not cancelled
            lambda: cancellable_sync_func("task2", 1.0),  # Would take long if not cancelled
            cancel_event=cancel_event,
            cancel_timeout=1.0,
            retry_settings=NO_RETRIES,
        )

        # Should be cancelled quickly since cancel_event is already set
        assert results2 == ["task1: cancelled", "task2: cancelled"]
        # Call counts should increment
        assert call_counts["task1"] == 2
        assert call_counts["task2"] == 2

    asyncio.run(run_test())
