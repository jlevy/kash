from __future__ import annotations

import asyncio
import threading
from typing import Any

from kash.utils.api_utils.api_retries import (
    NO_RETRIES,
    RetryExhaustedException,
    RetrySettings,
)
from kash.utils.api_utils.gather_limited import (
    FuncTask,
    Limit,
    gather_limited_async,
    gather_limited_sync,
)


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
            global_limit=Limit(concurrency=2, rps=10.0),
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
            global_limit=Limit(concurrency=2, rps=10.0),
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
                return_exceptions=False,  # Explicitly request exceptions to be raised
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
                return_exceptions=False,  # Explicitly request exceptions to be raised
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
                return_exceptions=False,  # Explicitly request exceptions to be raised
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


def test_gather_limited_bucket_limits():
    """Test bucket-based rate limiting with different limits per bucket."""
    import time

    async def run_test():
        call_times = {"api1": [], "api2": [], "default": []}

        def track_api_call(bucket: str, delay: float = 0.05) -> str:
            """Sync function that tracks call times per bucket."""
            call_times[bucket].append(time.time())
            time.sleep(delay)
            return f"{bucket}_result"

        # Test with different bucket limits
        results = await gather_limited_sync(
            FuncTask(track_api_call, ("api1",), bucket="api1"),
            FuncTask(track_api_call, ("api1",), bucket="api1"),
            FuncTask(track_api_call, ("api2",), bucket="api2"),
            FuncTask(track_api_call, ("api2",), bucket="api2"),
            FuncTask(track_api_call, ("default",)),  # Uses default bucket
            global_limit=Limit(concurrency=10, rps=100),  # High global limits
            bucket_limits={
                "api1": Limit(concurrency=1, rps=10),  # Very restricted
                "api2": Limit(concurrency=2, rps=20),  # Less restricted
                # default bucket has no specific limits, uses global
            },
            retry_settings=NO_RETRIES,
        )

        # Verify results
        assert results == [
            "api1_result",
            "api1_result",
            "api2_result",
            "api2_result",
            "default_result",
        ]

        # Verify that api1 calls were serialized (concurrency=1)
        api1_times = call_times["api1"]
        assert len(api1_times) == 2
        # Second call should start after first one finishes (due to concurrency=1)
        assert api1_times[1] >= api1_times[0] + 0.04  # Allow some timing tolerance

        # Verify that api2 calls could run concurrently (concurrency=2)
        api2_times = call_times["api2"]
        assert len(api2_times) == 2
        # Both calls should start close together (due to concurrency=2)
        assert abs(api2_times[1] - api2_times[0]) < 0.02  # Should start very close together

        # Verify default bucket had no specific restrictions
        default_times = call_times["default"]
        assert len(default_times) == 1

    asyncio.run(run_test())


def test_gather_limited_bucket_limits_async():
    """Test bucket-based rate limiting with async functions."""
    import asyncio
    import time

    async def run_test():
        call_times = {"fast_api": [], "slow_api": []}

        async def track_async_call(bucket: str, delay: float = 0.01) -> str:
            """Async function that tracks call times per bucket."""
            call_times[bucket].append(time.time())
            await asyncio.sleep(delay)
            return f"{bucket}_async_result"

        # Test with bucket limits on async functions
        results = await gather_limited_async(
            FuncTask(track_async_call, ("fast_api",), bucket="fast_api"),
            FuncTask(track_async_call, ("fast_api",), bucket="fast_api"),
            FuncTask(track_async_call, ("slow_api",), bucket="slow_api"),
            FuncTask(track_async_call, ("slow_api",), bucket="slow_api"),
            global_limit=Limit(concurrency=10, rps=100),  # High global limits
            bucket_limits={
                "fast_api": Limit(concurrency=2, rps=50),  # Can run both concurrently
                "slow_api": Limit(concurrency=1, rps=10),  # Must run serially
            },
            retry_settings=NO_RETRIES,
        )

        # Verify results
        assert results == [
            "fast_api_async_result",
            "fast_api_async_result",
            "slow_api_async_result",
            "slow_api_async_result",
        ]

        # Verify fast_api calls ran concurrently
        fast_times = call_times["fast_api"]
        assert len(fast_times) == 2
        assert abs(fast_times[1] - fast_times[0]) < 0.005  # Very close timing

        # Verify slow_api calls were serialized
        slow_times = call_times["slow_api"]
        assert len(slow_times) == 2
        assert slow_times[1] >= slow_times[0] + 0.005  # Sequential timing

    asyncio.run(run_test())


def test_gather_limited_mixed_buckets():
    """Test mixing FuncTask with bucket and regular callables."""
    import asyncio

    async def run_test():
        def simple_func(value: int) -> str:
            return f"simple_{value}"

        async def bucket_func(value: int) -> str:
            await asyncio.sleep(0.01)
            return f"bucket_{value}"

        # Mix FuncTask with buckets and regular callables
        results = await gather_limited_async(
            lambda: bucket_func(1),  # Regular callable, uses default bucket
            FuncTask(bucket_func, (2,), bucket="special"),  # Custom bucket
            lambda: bucket_func(3),  # Regular callable, uses default bucket
            global_limit=Limit(concurrency=5, rps=20),
            bucket_limits={
                "special": Limit(concurrency=1, rps=5),
                # default bucket uses global limits
            },
            retry_settings=NO_RETRIES,
        )

        assert results == ["bucket_1", "bucket_2", "bucket_3"]

    asyncio.run(run_test())


def test_gather_limited_bucket_backward_compatibility():
    """Test that the new API is backward compatible when no bucket_limits provided."""
    import asyncio

    async def run_test():
        def simple_sync(value: int) -> int:
            return value * 2

        async def simple_async(value: int) -> int:
            await asyncio.sleep(0.01)
            return value * 3

        # Test sync version without bucket_limits (should behave like old API)
        sync_results = await gather_limited_sync(
            lambda: simple_sync(1),
            lambda: simple_sync(2),
            global_limit=Limit(concurrency=2, rps=10),
            retry_settings=NO_RETRIES,
        )
        assert sync_results == [2, 4]

        # Test async version without bucket_limits (should behave like old API)
        async_results = await gather_limited_async(
            lambda: simple_async(1),
            lambda: simple_async(2),
            global_limit=Limit(concurrency=2, rps=10),
            retry_settings=NO_RETRIES,
        )
        assert async_results == [3, 6]

        # Test FuncTask without custom bucket (should use "default")
        mixed_results = await gather_limited_sync(
            FuncTask(simple_sync, (5,)),  # Uses default bucket
            lambda: simple_sync(6),  # Also uses default bucket
            global_limit=Limit(concurrency=2, rps=10),
            retry_settings=NO_RETRIES,
        )
        assert mixed_results == [10, 12]

    asyncio.run(run_test())


def test_gather_limited_bucket_fallback_star():
    """Test "*" fallback bucket limits when specific bucket limits are not provided."""
    import time

    async def run_test():
        call_times = {"api1": [], "api2": [], "api3": []}

        def track_api_call(bucket: str, delay: float = 0.05) -> str:
            """Sync function that tracks call times per bucket."""
            call_times[bucket].append(time.time())
            time.sleep(delay)
            return f"{bucket}_result"

        # Test with "*" fallback - api2 and api3 should use "*" limits
        results = await gather_limited_sync(
            FuncTask(track_api_call, ("api1",), bucket="api1"),
            FuncTask(track_api_call, ("api1",), bucket="api1"),
            FuncTask(track_api_call, ("api2",), bucket="api2"),  # Should use "*" fallback
            FuncTask(track_api_call, ("api2",), bucket="api2"),  # Should use "*" fallback
            FuncTask(track_api_call, ("api3",), bucket="api3"),  # Should use "*" fallback
            global_limit=Limit(concurrency=10, rps=100),  # High global limits
            bucket_limits={
                "api1": Limit(concurrency=1, rps=10),  # Specific limit for api1
                "*": Limit(concurrency=1, rps=10),  # Fallback for api2, api3
            },
            retry_settings=NO_RETRIES,
        )

        # Verify results
        assert results == [
            "api1_result",
            "api1_result",
            "api2_result",
            "api2_result",
            "api3_result",
        ]

        # Verify that api1 calls were serialized (concurrency=1 from specific limit)
        api1_times = call_times["api1"]
        assert len(api1_times) == 2
        assert api1_times[1] >= api1_times[0] + 0.04  # Second call after first finishes

        # Verify that api2 calls were also serialized (concurrency=1 from "*" fallback)
        api2_times = call_times["api2"]
        assert len(api2_times) == 2
        assert api2_times[1] >= api2_times[0] + 0.04  # Second call after first finishes

        # Verify that api3 used "*" fallback (only one call, but still good to check)
        api3_times = call_times["api3"]
        assert len(api3_times) == 1

    asyncio.run(run_test())


def test_gather_limited_bucket_fallback_star_async():
    """Test "*" fallback bucket limits with async functions."""
    import time

    async def run_test():
        call_times = {"service1": [], "service2": [], "service3": []}

        async def track_async_call(bucket: str, delay: float = 0.02) -> str:
            """Async function that tracks call times per bucket."""
            call_times[bucket].append(time.time())
            await asyncio.sleep(delay)
            return f"{bucket}_async_result"

        # Test with "*" fallback for async functions
        results = await gather_limited_async(
            FuncTask(track_async_call, ("service1",), bucket="service1"),
            FuncTask(track_async_call, ("service1",), bucket="service1"),
            FuncTask(track_async_call, ("service2",), bucket="service2"),  # Should use "*" fallback
            FuncTask(track_async_call, ("service3",), bucket="service3"),  # Should use "*" fallback
            global_limit=Limit(concurrency=10, rps=100),  # High global limits
            bucket_limits={
                "service1": Limit(concurrency=2, rps=20),  # Specific limit for service1
                "*": Limit(concurrency=1, rps=10),  # Fallback for service2, service3
            },
            retry_settings=NO_RETRIES,
        )

        # Verify results
        assert results == [
            "service1_async_result",
            "service1_async_result",
            "service2_async_result",
            "service3_async_result",
        ]

        # Verify that service1 calls could run concurrently (concurrency=2)
        service1_times = call_times["service1"]
        assert len(service1_times) == 2
        assert abs(service1_times[1] - service1_times[0]) < 0.01  # Should start close together

        # Verify that service2 and service3 used "*" fallback
        service2_times = call_times["service2"]
        service3_times = call_times["service3"]
        assert len(service2_times) == 1
        assert len(service3_times) == 1

    asyncio.run(run_test())


def test_gather_limited_bucket_priority_over_star():
    """Test that specific bucket limits take priority over "*" fallback."""
    import time

    async def run_test():
        call_times = {"priority_api": [], "fallback_api": []}

        def track_api_call(bucket: str, delay: float = 0.06) -> str:
            """Sync function that tracks call times per bucket."""
            call_times[bucket].append(time.time())
            time.sleep(delay)
            return f"{bucket}_result"

        # Test priority: specific bucket limits should override "*" fallback
        results = await gather_limited_sync(
            FuncTask(track_api_call, ("priority_api",), bucket="priority_api"),
            FuncTask(track_api_call, ("priority_api",), bucket="priority_api"),
            FuncTask(track_api_call, ("priority_api",), bucket="priority_api"),
            FuncTask(track_api_call, ("fallback_api",), bucket="fallback_api"),  # Uses "*"
            FuncTask(track_api_call, ("fallback_api",), bucket="fallback_api"),  # Uses "*"
            global_limit=Limit(concurrency=10, rps=100),  # High global limits
            bucket_limits={
                "priority_api": Limit(concurrency=2, rps=20),  # Specific: allows 2 concurrent
                "*": Limit(concurrency=1, rps=10),  # Fallback: allows 1 concurrent
            },
            retry_settings=NO_RETRIES,
        )

        # Verify results
        assert results == [
            "priority_api_result",
            "priority_api_result",
            "priority_api_result",
            "fallback_api_result",
            "fallback_api_result",
        ]

        # Verify that priority_api used specific limits (concurrency=2)
        priority_times = call_times["priority_api"]
        assert len(priority_times) == 3
        # First two should start close together due to concurrency=2
        assert abs(priority_times[1] - priority_times[0]) < 0.02
        # Third should start after one of the first two finishes
        assert priority_times[2] >= priority_times[0] + 0.05

        # Verify that fallback_api used "*" limits (concurrency=1)
        fallback_times = call_times["fallback_api"]
        assert len(fallback_times) == 2
        # Second call should start after first finishes due to concurrency=1
        assert fallback_times[1] >= fallback_times[0] + 0.05

    asyncio.run(run_test())


def test_gather_limited_bucket_star_only():
    """Test bucket limits with only "*" fallback and no specific buckets."""
    import time

    async def run_test():
        call_times = {"bucket1": [], "bucket2": [], "bucket3": []}

        def track_api_call(bucket: str, delay: float = 0.05) -> str:
            """Sync function that tracks call times per bucket."""
            call_times[bucket].append(time.time())
            time.sleep(delay)
            return f"{bucket}_result"

        # Test with only "*" fallback - all buckets should use same limits
        results = await gather_limited_sync(
            FuncTask(track_api_call, ("bucket1",), bucket="bucket1"),
            FuncTask(track_api_call, ("bucket1",), bucket="bucket1"),
            FuncTask(track_api_call, ("bucket2",), bucket="bucket2"),
            FuncTask(track_api_call, ("bucket3",), bucket="bucket3"),
            global_limit=Limit(concurrency=10, rps=100),  # High global limits
            bucket_limits={
                "*": Limit(concurrency=1, rps=10),  # All buckets use this fallback
            },
            retry_settings=NO_RETRIES,
        )

        # Verify results
        assert results == [
            "bucket1_result",
            "bucket1_result",
            "bucket2_result",
            "bucket3_result",
        ]

        # All buckets should use "*" limits (concurrency=1)
        # Verify bucket1 calls were serialized
        bucket1_times = call_times["bucket1"]
        assert len(bucket1_times) == 2
        assert bucket1_times[1] >= bucket1_times[0] + 0.04

        # Verify other buckets used the same fallback limits
        bucket2_times = call_times["bucket2"]
        bucket3_times = call_times["bucket3"]
        assert len(bucket2_times) == 1
        assert len(bucket3_times) == 1

    asyncio.run(run_test())


def test_gather_limited_bucket_no_star_fallback():
    """Test that buckets without specific limits and no "*" fallback use global limits."""
    import time

    async def run_test():
        call_times = {"fast_api": [], "slow_api": [], "unlimited_api": []}

        def track_api_call(bucket: str, delay: float = 0.03) -> str:
            """Sync function that tracks call times per bucket."""
            call_times[bucket].append(time.time())
            time.sleep(delay)
            return f"{bucket}_result"

        # Test without "*" fallback - unlimited_api should use global limits
        results = await gather_limited_sync(
            FuncTask(track_api_call, ("fast_api",), bucket="fast_api"),
            FuncTask(track_api_call, ("slow_api",), bucket="slow_api"),
            FuncTask(track_api_call, ("slow_api",), bucket="slow_api"),
            FuncTask(track_api_call, ("unlimited_api",), bucket="unlimited_api"),
            FuncTask(track_api_call, ("unlimited_api",), bucket="unlimited_api"),
            FuncTask(track_api_call, ("unlimited_api",), bucket="unlimited_api"),
            global_limit=Limit(concurrency=5, rps=50),  # Generous global limits
            bucket_limits={
                "fast_api": Limit(concurrency=3, rps=30),
                "slow_api": Limit(concurrency=1, rps=5),
                # No "*" fallback - unlimited_api uses global limits
            },
            retry_settings=NO_RETRIES,
        )

        # Verify results
        assert results == [
            "fast_api_result",
            "slow_api_result",
            "slow_api_result",
            "unlimited_api_result",
            "unlimited_api_result",
            "unlimited_api_result",
        ]

        # Verify slow_api was constrained (concurrency=1)
        slow_times = call_times["slow_api"]
        assert len(slow_times) == 2
        assert slow_times[1] >= slow_times[0] + 0.025

        # Verify unlimited_api could run concurrently (using global concurrency=5)
        unlimited_times = call_times["unlimited_api"]
        assert len(unlimited_times) == 3
        # All three should start close together since global concurrency=5 > 3 tasks
        time_diffs = [abs(unlimited_times[i] - unlimited_times[0]) for i in range(1, 3)]
        assert all(diff < 0.05 for diff in time_diffs)  # More reasonable tolerance

    asyncio.run(run_test())
