from __future__ import annotations

import asyncio
import random
import time
from typing import Any

from kash.utils.api_utils.api_retries import RetrySettings
from kash.utils.api_utils.gather_limited import gather_limited, gather_limited_sync
from kash.utils.api_utils.progress_protocol import SimpleProgressContext, TaskState
from kash.utils.rich_custom.task_status import StatusSettings, TaskStatus


class SimulatedAPIError(Exception):
    """Mock API error for testing retries."""

    pass


class SimulatedRateLimitError(Exception):
    """Mock rate limit error for testing retries."""

    pass


async def task_status_demo() -> dict[str, Any]:
    """
    Visual demo for TaskStatus.
    """
    results = {}

    # Demo: SimpleProgressTracker comparison
    print("\nDemo: SimpleProgressTracker")

    simple_call_count = 0

    async def simple_task(value: int) -> str:
        nonlocal simple_call_count
        simple_call_count += 1
        await asyncio.sleep(0.15)

        # Fail first call to show retry
        if simple_call_count == 1:
            raise SimulatedRateLimitError("First call always fails")

        return f"simple_result_{value}"

    async with SimpleProgressContext(verbose=True) as simple_status:
        simple_results = await gather_limited(
            lambda: simple_task(1),
            lambda: simple_task(2),
            lambda: simple_task(3),
            status=simple_status,
            labeler=lambda i, spec: f"Simple Task {i + 1}",
            retry_settings=RetrySettings(
                max_task_retries=2,
                initial_backoff=0.1,
                is_retriable=lambda e: isinstance(e, (SimulatedAPIError, SimulatedRateLimitError)),
            ),
        )

    results["simple_tracker"] = {"results": simple_results, "call_count": simple_call_count}

    # Demo: Basic API calls with retries
    print("\nDemo: API Calls with Retry Visualization")

    call_counts = {"api1": 0, "api2": 0, "api3": 0, "api4": 0}

    async def mock_api_call(endpoint: str, should_fail_times: int = 0) -> str:
        """Mock API call that fails specified number of times."""
        call_counts[endpoint] += 1
        current_call = call_counts[endpoint]

        # Variable work time
        await asyncio.sleep(random.uniform(0.1, 0.4))

        if current_call <= should_fail_times:
            if current_call <= should_fail_times // 2:
                raise SimulatedRateLimitError(f"Rate limit exceeded for {endpoint}")
            else:
                raise SimulatedAPIError(f"API error for {endpoint}")

        return f"success_{endpoint}"

    async with TaskStatus() as status:
        api_results = await gather_limited(
            lambda: mock_api_call("api1", should_fail_times=0),  # Immediate success
            lambda: mock_api_call("api2", should_fail_times=1),  # single retry
            lambda: mock_api_call("api3", should_fail_times=2),  # two retries
            lambda: mock_api_call("api4", should_fail_times=3),  # three retries
            status=status,
            labeler=lambda i, spec: f"API Endpoint {chr(ord('A') + i)}",
            retry_settings=RetrySettings(
                max_task_retries=4,
                initial_backoff=0.1,
                max_backoff=0.8,
                backoff_factor=1.5,
                is_retriable=lambda e: isinstance(e, (SimulatedAPIError, SimulatedRateLimitError)),
            ),
            max_concurrent=2,
            max_rps=5.0,
        )

    results["api_calls"] = {"results": api_results, "call_counts": call_counts.copy()}

    # Demo: Sync functions with different symbols
    print("\nDemo: Sync Functions with Custom Symbols")

    sync_call_counts = {"task1": 0, "task2": 0, "task3": 0}

    def mock_sync_work(name: str, fail_times: int = 0) -> str:
        """Mock sync work that can fail."""
        sync_call_counts[name] += 1
        current_call = sync_call_counts[name]

        time.sleep(random.uniform(0.1, 0.3))

        if current_call <= fail_times:
            raise SimulatedRateLimitError(f"Sync error for {name}")

        return f"sync_complete_{name}"

    async with TaskStatus(settings=StatusSettings(transient=False)) as status:
        sync_results = await gather_limited_sync(
            lambda: mock_sync_work("task1", fail_times=0),
            lambda: mock_sync_work("task2", fail_times=1),
            lambda: mock_sync_work("task3", fail_times=2),
            status=status,
            labeler=lambda i, spec: f"Sync Job {chr(ord('A') + i)}",
            retry_settings=RetrySettings(
                max_task_retries=3,
                initial_backoff=0.05,
                max_backoff=0.5,
                is_retriable=lambda e: isinstance(e, (SimulatedAPIError, SimulatedRateLimitError)),
            ),
        )

    results["sync_tasks"] = {"results": sync_results, "call_counts": sync_call_counts.copy()}

    # Demo: Manual task control with progress bars
    print("\nDemo: Manual Task Control & Progress Bars")

    async with TaskStatus(settings=StatusSettings(transient=False, show_progress=True)) as status:
        # Create tasks with different progress patterns
        task1 = await status.add("Data Processing", total=10)
        task2 = await status.add("File Upload", total=5)
        task3 = await status.add("Analytics", total=8)

        # Simulate complex work patterns
        tasks_info = []

        # Task: Steady progress with one retry
        for i in range(5):
            await asyncio.sleep(0.2)
            await status.update(task1, progress=1)
            await status.update(task1, label=f"Processing batch {i + 1}/10")

        # Simulate retry on task
        await status.update(task1, error_msg="Network timeout during batch 6")
        await asyncio.sleep(0.3)

        # Complete task
        for i in range(5, 10):
            await asyncio.sleep(0.15)
            await status.update(task1, progress=1)
            await status.update(task1, label=f"Processing batch {i + 1}/10")

        await status.finish(task1, TaskState.COMPLETED)
        tasks_info.append(status.get_task_info(task1))

        # Upload task with multiple retries then success
        for i in range(2):
            await asyncio.sleep(0.2)
            await status.update(task2, progress=1)

        # Multiple retries
        await status.update(task2, error_msg="Connection reset")
        await asyncio.sleep(0.2)
        await status.update(task2, error_msg="Upload timeout")
        await asyncio.sleep(0.2)

        # Complete upload
        for i in range(2, 5):
            await asyncio.sleep(0.15)
            await status.update(task2, progress=1)

        await status.finish(task2, TaskState.COMPLETED)
        tasks_info.append(status.get_task_info(task2))

        # Analytics task that fails after retries
        for i in range(4):
            await asyncio.sleep(0.1)
            await status.update(task3, progress=1)
            if i == 2:
                await status.update(task3, error_msg="Temporary server error")
                await asyncio.sleep(0.2)

        # Final failure
        await status.finish(task3, TaskState.FAILED, "Permanent server error")
        tasks_info.append(status.get_task_info(task3))

        results["manual_tasks"] = {
            "task_info": [
                (info.retry_count, info.state.value, len(info.failures))
                for info in tasks_info
                if info
            ]
        }

    # Demo: Mixed success/failure scenarios
    print("\nDemo: Mixed Success/Failure Scenarios")

    failure_call_counts = {"recoverable": 0, "unrecoverable": 0}

    async def recoverable_task() -> str:
        failure_call_counts["recoverable"] += 1
        await asyncio.sleep(0.1)

        if failure_call_counts["recoverable"] <= 2:
            raise SimulatedRateLimitError("Recoverable failure")

        return "recovered_successfully"

    async def unrecoverable_task() -> str:
        failure_call_counts["unrecoverable"] += 1
        await asyncio.sleep(0.05)
        raise SimulatedAPIError("Permanent system failure")

    async with TaskStatus(
        settings=StatusSettings(
            success_symbol="✨", failure_symbol="💀", retry_symbol="🔥", transient=False
        )
    ) as status:
        mixed_results = await gather_limited(
            recoverable_task,
            unrecoverable_task,
            status=status,
            labeler=lambda i, spec: f"Mixed Task {chr(ord('A') + i)}",
            retry_settings=RetrySettings(
                max_task_retries=3,
                initial_backoff=0.05,
                max_backoff=0.3,
                is_retriable=lambda e: isinstance(e, (SimulatedAPIError, SimulatedRateLimitError)),
            ),
            return_exceptions=True,
        )

    results["mixed_scenarios"] = {
        "results": mixed_results,
        "call_counts": failure_call_counts.copy(),
    }

    print(f"\nDemo completed! Generated {len(results)} result sets.")
    return results


def test_comprehensive_task_status_demo():
    """Simple pytest wrapper for the demo with basic sanity checks."""

    # Run the demo
    demo_results = asyncio.run(task_status_demo())

    # Basic sanity checks
    assert "api_calls" in demo_results
    assert "sync_tasks" in demo_results
    assert "manual_tasks" in demo_results
    assert "simple_tracker" in demo_results
    assert "mixed_scenarios" in demo_results

    # Check API calls worked
    api_data = demo_results["api_calls"]
    assert len(api_data["results"]) == 4
    assert all("success_" in result for result in api_data["results"])

    # Verify retry counts match expected failure patterns
    call_counts = api_data["call_counts"]
    assert call_counts["api1"] == 1  # No retries
    assert call_counts["api2"] == 2  # failure + success
    assert call_counts["api3"] == 3  # two failures + success
    assert call_counts["api4"] == 4  # three failures + success

    # Check sync tasks
    sync_data = demo_results["sync_tasks"]
    assert len(sync_data["results"]) == 3
    assert all("sync_complete_" in result for result in sync_data["results"])

    # Check manual task info
    manual_data = demo_results["manual_tasks"]
    task_info = manual_data["task_info"]
    assert len(task_info) == 3

    # First task: single retry, completed, failure recorded
    assert task_info[0] == (1, "completed", 1)
    # Second task: two retries, completed, failures recorded
    assert task_info[1] == (2, "completed", 2)
    # Third task: single retry, failed, failures recorded (manual retry + from fail())
    assert task_info[2] == (1, "failed", 2)

    # Check simple tracker worked
    simple_data = demo_results["simple_tracker"]
    assert len(simple_data["results"]) == 3
    assert simple_data["call_count"] >= 3  # At least one call per task, plus retries

    # Check mixed scenarios
    mixed_data = demo_results["mixed_scenarios"]
    results = mixed_data["results"]
    assert len(results) == 2
    assert results[0] == "recovered_successfully"  # Should recover after retries
    assert isinstance(results[1], Exception)  # Should remain as exception

    print("All sanity checks passed!")


if __name__ == "__main__":
    asyncio.run(task_status_demo())
