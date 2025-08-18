from __future__ import annotations

import asyncio
import inspect
import logging
import threading
import time
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any, Generic, TypeAlias, TypeVar, cast, overload

from aiolimiter import AsyncLimiter

from kash.utils.api_utils.api_retries import (
    DEFAULT_RETRIES,
    NO_RETRIES,
    RetryExhaustedException,
    RetrySettings,
    calculate_backoff,
    extract_http_status_code,
)
from kash.utils.api_utils.progress_protocol import Labeler, ProgressTracker, TaskState

T = TypeVar("T")

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Limit:
    """
    Rate limiting configuration with max RPS and max concurrency.
    """

    rps: float
    concurrency: int


DEFAULT_CANCEL_TIMEOUT: float = 1.0


@dataclass(frozen=True)
class TaskResult(Generic[T]):
    """
    Optional wrapper for task results that can signal rate limiting behavior.
    Use this to wrap results that should bypass rate limiting (e.g., cache hits).
    """

    value: T
    disable_limits: bool = False


@dataclass(frozen=True)
class FuncTask(Generic[T]):
    """
    A task described as an unevaluated function with args and kwargs.
    This task format allows you to use args and kwargs in the Labeler.
    It also allows specifying a bucket for rate limiting.

    For async functions: The function should return a coroutine that yields either `T` or `TaskResult[T]`.
    For sync functions: The function should return either `T` or `TaskResult[T]` directly.

    Using `TaskResult[T]` allows controlling rate limiting behavior (e.g., cache hits can bypass rate limits).
    """

    func: Callable[..., Any]  # Keep as Any since it can be sync or async
    args: tuple[Any, ...] = ()
    kwargs: dict[str, Any] = field(default_factory=dict)
    bucket: str = "default"


# Type aliases for coroutine and sync specifications, including unevaluated function specs
CoroSpec: TypeAlias = (
    Callable[[], Coroutine[None, None, T]] | Coroutine[None, None, T] | FuncTask[T]
)
SyncSpec: TypeAlias = Callable[[], T] | FuncTask[T]

# Specific labeler types using the generic Labeler pattern
CoroLabeler: TypeAlias = Labeler[CoroSpec[T]]
SyncLabeler: TypeAlias = Labeler[SyncSpec[T]]


def _get_bucket_limits(
    bucket: str,
    bucket_semaphores: dict[str, asyncio.Semaphore],
    bucket_rate_limiters: dict[str, AsyncLimiter],
) -> tuple[asyncio.Semaphore | None, AsyncLimiter | None]:
    """
    Get bucket-specific limits with fallback to "*" wildcard.

    Checks for exact bucket match first, then falls back to "*" if available.
    Returns (None, None) if neither exact match nor "*" fallback exists.
    """
    # Try exact bucket match first
    bucket_semaphore = bucket_semaphores.get(bucket)
    bucket_rate_limiter = bucket_rate_limiters.get(bucket)

    if bucket_semaphore is not None and bucket_rate_limiter is not None:
        return bucket_semaphore, bucket_rate_limiter

    # Fall back to "*" wildcard if available
    bucket_semaphore = bucket_semaphores.get("*")
    bucket_rate_limiter = bucket_rate_limiters.get("*")

    return bucket_semaphore, bucket_rate_limiter


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
    limit: Limit | None,
    bucket_limits: dict[str, Limit] | None = None,
    return_exceptions: bool = False,
    retry_settings: RetrySettings | None = DEFAULT_RETRIES,
    status: ProgressTracker | None = None,
    labeler: CoroLabeler[T] | None = None,
) -> list[T]: ...


@overload
async def gather_limited_async(
    *coro_specs: CoroSpec[T],
    limit: Limit | None,
    bucket_limits: dict[str, Limit] | None = None,
    return_exceptions: bool = True,
    retry_settings: RetrySettings | None = DEFAULT_RETRIES,
    status: ProgressTracker | None = None,
    labeler: CoroLabeler[T] | None = None,
) -> list[T | BaseException]: ...


async def gather_limited_async(
    *coro_specs: CoroSpec[T],
    limit: Limit | None,
    bucket_limits: dict[str, Limit] | None = None,
    return_exceptions: bool = True,  # Default to True for resilient batch operations
    retry_settings: RetrySettings | None = DEFAULT_RETRIES,
    status: ProgressTracker | None = None,
    labeler: CoroLabeler[T] | None = None,
) -> list[T] | list[T | BaseException]:
    """
    Rate-limited version of `asyncio.gather()` with HTTP-aware retry logic and optional progress display.
    Uses the aiolimiter leaky-bucket algorithm with exponential backoff on failures.

    Supports two levels of retry limits:
    - Per-task retries: max_task_retries attempts per individual task
    - Global retries: max_total_retries attempts across all tasks (prevents cascade failures)

    Features HTTP-aware retry classification:
    - Automatically detects HTTP status codes (403, 429, 500, etc.) and applies appropriate retry behavior
    - Configurable handling of conditional status codes like 403 Forbidden
    - Defaults to return_exceptions=True for resilient batch operations

    Prevents API flooding during rate limit backoffs:
    - Semaphore slots are held during entire retry cycles, including backoff periods
    - New tasks cannot start while existing tasks are backing off from rate limits
    - Rate limiters are only acquired during actual execution attempts

    Can optionally display live progress with retry indicators using TaskStatus.

    Accepts:
    - Callables that return coroutines: `lambda: some_async_func(arg)` (recommended for retries)
    - Coroutines directly: `some_async_func(arg)` (only if retries disabled)
    - FuncTask objects: `FuncTask(some_async_func, (arg1, arg2), {"kwarg": value})` (args accessible to labeler)

    Functions can return `TaskResult[T]` to bypass rate limiting for specific results:
    - `TaskResult(value, disable_limits=True)`: bypass rate limiting (e.g., cache hits)
    - `TaskResult(value, disable_limits=False)`: apply normal rate limiting
    - `value` directly: apply normal rate limiting

    Examples:
        ```python
        # With progress display and custom labeling:
        from kash.utils.rich_custom.task_status import TaskStatus

        async with TaskStatus() as status:
            await gather_limited_async(
                lambda: fetch_url("http://example.com"),
                lambda: process_data(data),
                status=status,
                labeler=lambda i, spec: f"Task {i+1}",
                retry_settings=RetrySettings(max_task_retries=3, max_total_retries=25)
            )

        # Without progress display:
        await gather_limited_async(
            lambda: fetch_url("http://example.com"),
            lambda: process_data(data),
            retry_settings=RetrySettings(max_task_retries=3, max_total_retries=25)
        )

        # With bucket-specific limits and "*" fallback:
        await gather_limited_async(
            FuncTask(fetch_api, ("data1",), bucket="api1"),
            FuncTask(fetch_api, ("data2",), bucket="api2"),
            FuncTask(fetch_api, ("data3",), bucket="api3"),
            limit=Limit(rps=100, concurrency=50),
            bucket_limits={
                "api1": Limit(rps=20, concurrency=10),  # Specific limit for api1
                "*": Limit(rps=15, concurrency=8),      # Fallback for api2, api3, and others
            }
        )

        # With cache bypass using TaskResult:
        async def fetch_with_cache(url: str) -> TaskResult[dict] | dict:
            cached_data = await cache.get(url)
            if cached_data:
                return TaskResult(cached_data, disable_limits=True)  # Cache hit: no rate limit

            data = await fetch_api(url)  # Will be rate limited
            await cache.set(url, data)
            return data

        await gather_limited_async(
            lambda: fetch_with_cache("http://api.com/data1"),
            lambda: fetch_with_cache("http://api.com/data2"),
            limit=Limit(rps=10, concurrency=5)  # Cache hits bypass these limits
        )

        ```

    Args:
        *coro_specs: Callables or coroutines to execute
        limit: Global limits applied to all tasks regardless of bucket
        bucket_limits: Optional per-bucket limits. Tasks use their bucket field to determine limits.
                      Use "*" as a fallback limit for buckets without specific limits.
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
        limit.concurrency if limit else "None",
        limit.rps if limit else "None",
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
    global_semaphore = asyncio.Semaphore(limit.concurrency) if limit else None
    global_rate_limiter = AsyncLimiter(limit.rps, 1.0) if limit else None

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
        bucket_semaphore, bucket_rate_limiter = _get_bucket_limits(
            bucket, bucket_semaphores, bucket_rate_limiters
        )

        async def executor() -> T:
            # Create a fresh coroutine for each attempt
            if isinstance(coro_spec, FuncTask):
                # FuncSpec format: FuncSpec(func, args, kwargs)
                coro = coro_spec.func(*coro_spec.args, **coro_spec.kwargs)
            elif callable(coro_spec):
                coro = coro_spec()
            else:
                # Direct coroutine: only valid if retries disabled
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
    limit: Limit | None,
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
    limit: Limit | None,
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
    limit: Limit | None,
    bucket_limits: dict[str, Limit] | None = None,
    return_exceptions: bool = True,  # Default to True for resilient batch operations
    retry_settings: RetrySettings | None = DEFAULT_RETRIES,
    status: ProgressTracker | None = None,
    labeler: SyncLabeler[T] | None = None,
    cancel_event: threading.Event | None = None,
    cancel_timeout: float = DEFAULT_CANCEL_TIMEOUT,
) -> list[T] | list[T | BaseException]:
    """
    Sync version of `gather_limited_async()` that executes synchronous functions with the same
    rate limiting, retry logic, and progress tracking capabilities.
    See `gather_limited_async()` for details.

    Sync-specific differences:

    **Function Execution**: Runs sync functions via `asyncio.to_thread()` instead of executing
    coroutines directly. Validates that callables don't accidentally return coroutines.

    **Cancellation Support**: Provides cooperative cancellation for long-running sync functions
    through optional `cancel_event` and graceful thread termination.

    **Input Validation**: Ensures sync functions don't return coroutines, which would indicate
    incorrect usage (async functions should use `gather_limited_async()`).

    Args:
        *sync_specs: Callables that return values (not coroutines) or FuncTask objects.
                    Functions can return `TaskResult[T]` to control rate limiting behavior.
        cancel_event: Optional threading.Event that will be set on cancellation
        cancel_timeout: Max seconds to wait for threads to terminate on cancellation
        (All other args identical to gather_limited_async())

    Returns:
        List of results in the same order as input specifications

    Example:
        ```python
        # Basic usage with sync functions
        results = await gather_limited_sync(
            lambda: some_sync_function(arg1),
            lambda: another_sync_function(arg2),
            limit=Limit(rps=2.0, concurrency=3),
            retry_settings=RetrySettings(max_task_retries=3, max_total_retries=25)
        )

        # With bucket-specific limits and "*" fallback
        results = await gather_limited_sync(
            FuncTask(fetch_from_api, ("data1",), bucket="api1"),
            FuncTask(fetch_from_api, ("data2",), bucket="api2"),
            FuncTask(fetch_from_api, ("data3",), bucket="api3"),
            limit=Limit(rps=100, concurrency=50),
            bucket_limits={
                "api1": Limit(rps=20, concurrency=10),  # Specific limit for api1
                "*": Limit(rps=15, concurrency=8),      # Fallback for api2, api3, and others
            }
        )

        # With cache bypass using TaskResult
        def sync_fetch_with_cache(url: str) -> TaskResult[dict] | dict:
            cached_data = cache.get_sync(url)
            if cached_data:
                return TaskResult(cached_data, disable_limits=True)  # Cache hit: no rate limit

            data = requests.get(url).json()  # Will be rate limited
            cache.set_sync(url, data)
            return data

        results = await gather_limited_sync(
            lambda: sync_fetch_with_cache("http://api.com/data1"),
            lambda: sync_fetch_with_cache("http://api.com/data2"),
            limit=Limit(rps=5, concurrency=3)  # Cache hits bypass these limits
        )
        ```
    """
    log.info(
        "Executing with global limits: concurrency %s at %s rps, %s",
        limit.concurrency if limit else "None",
        limit.rps if limit else "None",
        retry_settings,
    )
    if not sync_specs:
        return []

    retry_settings = retry_settings or NO_RETRIES

    # Global limits (apply to all tasks regardless of bucket)
    global_semaphore = asyncio.Semaphore(limit.concurrency) if limit else None
    global_rate_limiter = AsyncLimiter(limit.rps, 1.0) if limit else None

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
        bucket_semaphore, bucket_rate_limiter = _get_bucket_limits(
            bucket, bucket_semaphores, bucket_rate_limiters
        )

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

            log.warning("Task failed: %s: %s", label, e, exc_info=True)
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
    global_semaphore: asyncio.Semaphore | None,
    global_rate_limiter: AsyncLimiter | None,
    bucket_semaphore: asyncio.Semaphore | None,
    bucket_rate_limiter: AsyncLimiter | None,
    global_retry_counter: RetryCounter,
    status: ProgressTracker | None = None,
    task_id: Any | None = None,
) -> T:
    """
    Execute a task with retry logic, holding semaphores for the entire retry cycle.

    Semaphores are held during backoff periods to prevent API flooding when tasks
    are already backing off from rate limits. Only rate limiters are acquired/released
    for each execution attempt.
    """
    # Acquire semaphores once for the entire retry cycle (including backoff periods)
    if global_semaphore is not None:
        async with global_semaphore:
            if bucket_semaphore is not None:
                async with bucket_semaphore:
                    return await _execute_with_retry_inner(
                        executor,
                        retry_settings,
                        global_rate_limiter,
                        bucket_rate_limiter,
                        global_retry_counter,
                        status,
                        task_id,
                    )
            else:
                return await _execute_with_retry_inner(
                    executor,
                    retry_settings,
                    global_rate_limiter,
                    None,
                    global_retry_counter,
                    status,
                    task_id,
                )
    else:
        # No global semaphore, check bucket semaphore
        if bucket_semaphore is not None:
            async with bucket_semaphore:
                return await _execute_with_retry_inner(
                    executor,
                    retry_settings,
                    global_rate_limiter,
                    bucket_rate_limiter,
                    global_retry_counter,
                    status,
                    task_id,
                )
        else:
            # No semaphores at all, go straight to running
            return await _execute_with_retry_inner(
                executor,
                retry_settings,
                global_rate_limiter,
                None,
                global_retry_counter,
                status,
                task_id,
            )


async def _execute_with_retry_inner(
    executor: Callable[[], Coroutine[None, None, T]],
    retry_settings: RetrySettings,
    global_rate_limiter: AsyncLimiter | None,
    bucket_rate_limiter: AsyncLimiter | None,
    global_retry_counter: RetryCounter,
    status: ProgressTracker | None = None,
    task_id: Any | None = None,
) -> T:
    """
    Inner retry logic that handles rate limiting and backoff.

    This function assumes semaphores are already held by the caller and only
    manages rate limiters for each execution attempt.
    """
    if status and task_id:
        await status.start(task_id)

    start_time = time.time()
    last_exception: Exception | None = None

    for attempt in range(retry_settings.max_task_retries + 1):
        # Handle backoff before acquiring rate limiters (semaphores remain held)
        if attempt > 0 and last_exception:
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
            if status and task_id:
                # Include retry attempt info and backoff time in the status display
                retry_info = (
                    f"Attempt {attempt}/{retry_settings.max_task_retries} "
                    f"(waiting {backoff_time:.1f}s): {type(last_exception).__name__}: {last_exception}"
                )
                await status.update(task_id, TaskState.WAITING, error_msg=retry_info)

                # Use debug level for Rich trackers, warning/info for console trackers
                use_debug_level = status.suppress_logs
            else:
                # No status display: use full logging
                use_debug_level = False

            # Log retry information at appropriate level
            status_code = extract_http_status_code(last_exception)
            status_info = f" (HTTP {status_code})" if status_code else ""

            rate_limit_msg = (
                f"Rate limit hit{status_info} (attempt {attempt}/{retry_settings.max_task_retries} "
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

            # Sleep during backoff while holding semaphore slots
            await asyncio.sleep(backoff_time)

            # Set state back to running before next attempt
            if status and task_id:
                await status.update(task_id, TaskState.RUNNING)

        try:
            # Execute task to check for potential rate limit bypass
            raw_result = await executor()

            # Check if result indicates limits should be disabled (e.g., cache hit)
            if isinstance(raw_result, TaskResult):
                if raw_result.disable_limits:
                    # Bypass rate limiting and return immediately
                    return cast(T, raw_result.value)
                else:
                    # Wrapped but limits enabled: extract value for rate limiting
                    result_value = cast(T, raw_result.value)
            else:
                # Unwrapped result: apply normal rate limiting
                result_value = cast(T, raw_result)

            # Apply rate limiting for non-bypassed results
            if global_rate_limiter is not None:
                async with global_rate_limiter:
                    if bucket_rate_limiter is not None:
                        async with bucket_rate_limiter:
                            return result_value
                    else:
                        return result_value
            else:
                # No global rate limiter, check bucket rate limiter
                if bucket_rate_limiter is not None:
                    async with bucket_rate_limiter:
                        return result_value
                else:
                    # No rate limiting at all
                    return result_value

        except Exception as e:
            last_exception = e  # Always store the exception

            if attempt == retry_settings.max_task_retries:
                # Final attempt failed
                if retry_settings.max_task_retries == 0:
                    # No retries configured: raise original exception directly
                    raise
                else:
                    # Retries were attempted but exhausted: wrap with context
                    total_time = time.time() - start_time
                    log.error(
                        f"Max task retries ({retry_settings.max_task_retries}) exhausted after {total_time:.1f}s. "
                        f"Final attempt failed with: {type(e).__name__}: {e}"
                    )
                    raise RetryExhaustedException(e, retry_settings.max_task_retries, total_time)

            # Check if this is a retriable exception using the centralized logic
            if retry_settings.should_retry(e):
                # Continue to next retry attempt (semaphores remain held for backoff)
                continue
            else:
                # Non-retriable exception, log and re-raise immediately
                status_code = extract_http_status_code(e)
                status_info = f" (HTTP {status_code})" if status_code else ""

                log.warning("Non-retriable exception%s (not retrying): %s", status_info, e)
                log.debug("Exception traceback:", exc_info=True)
                raise

    # This should never be reached, but satisfy type checker
    raise RuntimeError("Unexpected code path in _execute_with_retry_inner")
