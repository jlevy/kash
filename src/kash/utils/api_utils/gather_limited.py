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

DEFAULT_MAX_CONCURRENT: int = 5
DEFAULT_MAX_RPS: float = 5.0
DEFAULT_CANCEL_TIMEOUT: float = 1.0


@dataclass(frozen=True)
class Limit:
    """
    Rate limiting configuration with max RPS and max concurrency.
    """

    rps: float = DEFAULT_MAX_RPS
    concurrency: int = DEFAULT_MAX_CONCURRENT


@dataclass(frozen=True)
class FuncTask:
    """
    A task described as an unevaluated function with args and kwargs.
    This task format allows you to use args and kwargs in the Labeler.
    """

    func: Callable[..., Any]
    args: tuple[Any, ...] = ()
    kwargs: dict[str, Any] = field(default_factory=dict)
    bucket: str = "default"


# Type aliases for coroutine and sync specifications, including unevaluated function specs
CoroSpec: TypeAlias = Callable[[], Coroutine[None, None, T]] | Coroutine[None, None, T] | FuncTask
SyncSpec: TypeAlias = Callable[[], T] | FuncTask

# Specific labeler types using the generic Labeler pattern
CoroLabeler: TypeAlias = Labeler[CoroSpec[T]]
SyncLabeler: TypeAlias = Labeler[SyncSpec[T]]


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
    global_limit: Limit = Limit(),
    bucket_limits: dict[str, Limit] | None = None,
    return_exceptions: bool = False,
    retry_settings: RetrySettings | None = DEFAULT_RETRIES,
    status: ProgressTracker | None = None,
    labeler: CoroLabeler[T] | None = None,
) -> list[T]: ...


@overload
async def gather_limited_async(
    *coro_specs: CoroSpec[T],
    global_limit: Limit = Limit(),
    bucket_limits: dict[str, Limit] | None = None,
    return_exceptions: bool = True,
    retry_settings: RetrySettings | None = DEFAULT_RETRIES,
    status: ProgressTracker | None = None,
    labeler: CoroLabeler[T] | None = None,
) -> list[T | BaseException]: ...


async def gather_limited_async(
    *coro_specs: CoroSpec[T],
    global_limit: Limit = Limit(),
    bucket_limits: dict[str, Limit] | None = None,
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
        "Executing with global limits: concurrency %s at %s rps, %s",
        global_limit.concurrency,
        global_limit.rps,
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

    # Global limits (apply to all tasks regardless of bucket)
    global_semaphore = asyncio.Semaphore(global_limit.concurrency)
    global_rate_limiter = AsyncLimiter(global_limit.rps, 1.0)

    # Per-bucket limits (if bucket_limits provided)
    bucket_semaphores: dict[str, asyncio.Semaphore] = {}
    bucket_rate_limiters: dict[str, AsyncLimiter] = {}

    if bucket_limits:
        for bucket_name, limit in bucket_limits.items():
            bucket_semaphores[bucket_name] = asyncio.Semaphore(limit.concurrency)
            bucket_rate_limiters[bucket_name] = AsyncLimiter(limit.rps, 1.0)

    # Global retry counter (shared across all tasks)
    global_retry_counter = RetryCounter(retry_settings.max_total_retries)

    async def run_task_with_retry(i: int, coro_spec: CoroSpec[T]) -> T:
        # Generate label for this task
        label = labeler(i, coro_spec) if labeler else f"task:{i}"
        task_id = await status.add(label) if status else None

        # Determine bucket and get appropriate limits
        bucket = "default"
        if isinstance(coro_spec, FuncTask):
            bucket = coro_spec.bucket

        # Get bucket-specific limits if available
        bucket_semaphore = bucket_semaphores.get(bucket)
        bucket_rate_limiter = bucket_rate_limiters.get(bucket)

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
                global_semaphore,
                global_rate_limiter,
                bucket_semaphore,
                bucket_rate_limiter,
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
    global_limit: Limit = Limit(),
    bucket_limits: dict[str, Limit] | None = None,
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
    global_limit: Limit = Limit(),
    bucket_limits: dict[str, Limit] | None = None,
    return_exceptions: bool = True,
    retry_settings: RetrySettings | None = DEFAULT_RETRIES,
    status: ProgressTracker | None = None,
    labeler: SyncLabeler[T] | None = None,
    cancel_event: threading.Event | None = None,
    cancel_timeout: float = DEFAULT_CANCEL_TIMEOUT,
) -> list[T | BaseException]: ...


async def gather_limited_sync(
    *sync_specs: SyncSpec[T],
    global_limit: Limit = Limit(),
    bucket_limits: dict[str, Limit] | None = None,
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
        global_limit: Global limits applied to all tasks regardless of bucket
        bucket_limits: Optional per-bucket limits. Tasks use their bucket field to determine limits.
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
        # Without bucket limits (backward compatible)
        results = await gather_limited_sync(
            lambda: some_sync_function(arg1),
            lambda: another_sync_function(arg2),
            global_limit=Limit(rps=2.0, concurrency=3),
            retry_settings=RetrySettings(max_task_retries=3, max_total_retries=25)
        )

        # With bucket-specific limits
        results = await gather_limited_sync(
            FuncTask(fetch_from_api, ("data1",), bucket="api1"),
            FuncTask(fetch_from_api, ("data2",), bucket="api2"),
            global_limit=Limit(rps=100, concurrency=50),
            bucket_limits={
                "api1": Limit(rps=20, concurrency=10),
                "api2": Limit(rps=30, concurrency=15),
            }
        )
        ```
    """
    log.info(
        "Executing with global limits: concurrency %s at %s rps, %s",
        global_limit.concurrency,
        global_limit.rps,
        retry_settings,
    )
    if not sync_specs:
        return []

    retry_settings = retry_settings or NO_RETRIES

    # Global limits (apply to all tasks regardless of bucket)
    global_semaphore = asyncio.Semaphore(global_limit.concurrency)
    global_rate_limiter = AsyncLimiter(global_limit.rps, 1.0)

    # Per-bucket limits (if bucket_limits provided)
    bucket_semaphores: dict[str, asyncio.Semaphore] = {}
    bucket_rate_limiters: dict[str, AsyncLimiter] = {}

    if bucket_limits:
        for bucket_name, limit in bucket_limits.items():
            bucket_semaphores[bucket_name] = asyncio.Semaphore(limit.concurrency)
            bucket_rate_limiters[bucket_name] = AsyncLimiter(limit.rps, 1.0)

    # Global retry counter (shared across all tasks)
    global_retry_counter = RetryCounter(retry_settings.max_total_retries)

    async def run_task_with_retry(i: int, sync_spec: SyncSpec[T]) -> T:
        # Generate label for this task
        label = labeler(i, sync_spec) if labeler else f"task:{i}"
        task_id = await status.add(label) if status else None

        # Determine bucket and get appropriate limits
        bucket = "default"
        if isinstance(sync_spec, FuncTask):
            bucket = sync_spec.bucket

        # Get bucket-specific limits if available
        bucket_semaphore = bucket_semaphores.get(bucket)
        bucket_rate_limiter = bucket_rate_limiters.get(bucket)

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
                global_semaphore,
                global_rate_limiter,
                bucket_semaphore,
                bucket_rate_limiter,
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
                    asyncio.gather(*async_tasks, return_exceptions=True),
                    timeout=cancel_timeout,
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
    global_semaphore: asyncio.Semaphore,
    global_rate_limiter: AsyncLimiter,
    bucket_semaphore: asyncio.Semaphore | None,
    bucket_rate_limiter: AsyncLimiter | None,
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
            # Acquire global limits first, then bucket-specific limits if present
            async with global_semaphore, global_rate_limiter:
                if bucket_semaphore is not None and bucket_rate_limiter is not None:
                    async with bucket_semaphore, bucket_rate_limiter:
                        # Mark task as started now that we've passed rate limiting
                        if status and task_id is not None and attempt == 0:
                            await status.start(task_id)
                        return await executor()
                else:
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
