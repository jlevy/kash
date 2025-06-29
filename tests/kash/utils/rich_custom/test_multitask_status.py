from __future__ import annotations

import asyncio
import random
import time
from typing import Any

from kash.utils.api_utils.api_retries import RetrySettings
from kash.utils.api_utils.gather_limited import (
    FuncTask,
    Limit,
    gather_limited_async,
    gather_limited_sync,
)
from kash.utils.api_utils.progress_protocol import SimpleProgressContext, TaskState
from kash.utils.common.testing import enable_if
from kash.utils.rich_custom.multitask_status import MultiTaskStatus, StatusSettings, StatusStyles


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
        simple_results = await gather_limited_async(
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

    async with MultiTaskStatus() as status:
        api_results = await gather_limited_async(
            lambda: mock_api_call("api1", should_fail_times=0),  # Immediate success
            lambda: mock_api_call("api2", should_fail_times=1),  # single retry
            lambda: mock_api_call("api3", should_fail_times=2),  # two retries
            lambda: mock_api_call("api4", should_fail_times=3),  # three retries
            global_limit=Limit(concurrency=2, rps=5.0),
            status=status,
            labeler=lambda i, spec: f"API Endpoint {chr(ord('A') + i)}",
            retry_settings=RetrySettings(
                max_task_retries=4,
                initial_backoff=0.1,
                max_backoff=0.8,
                backoff_factor=1.5,
                is_retriable=lambda e: isinstance(e, (SimulatedAPIError, SimulatedRateLimitError)),
            ),
        )

    results["api_calls"] = {"results": api_results, "call_counts": call_counts.copy()}

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

    async with MultiTaskStatus(settings=StatusSettings(transient=False)) as status:
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

    # Demo: FuncSpec format with custom labeler extracting args
    print("\nDemo: FuncSpec Format with Custom Labeler")

    task_call_count = 0

    async def process_task(input_data: str) -> str:
        """Simple task that takes input data and sleeps."""
        nonlocal task_call_count
        task_call_count += 1
        await asyncio.sleep(random.uniform(0.1, 0.4))

        # Simulate occasional failure on first call
        if task_call_count == 1 and len(input_data) > 20:
            raise SimulatedRateLimitError("Rate limit processing large input")

        return f"processed_{input_data[:10]}"

    def simple_labeler(i: int, spec: Any) -> str:
        """Custom labeler that shows input data from args."""
        if isinstance(spec, FuncTask):
            if spec.args and len(spec.args) > 0:
                input_data = str(spec.args[0])
                # Truncate long inputs for display
                truncated = input_data[:30] + "..." if len(input_data) > 30 else input_data
                return f"Processing: {truncated}"

        # Fallback for non-FuncSpec specs
        return f"Task {i + 1}"

    async with MultiTaskStatus(settings=StatusSettings(transient=False)) as status:
        funcspec_results = await gather_limited_async(
            FuncTask(process_task, ("short_input",)),  # Should succeed
            FuncTask(
                process_task, ("this_is_a_very_long_input_string_that_will_trigger_retry",)
            ),  # Should retry
            FuncTask(process_task, ("medium_length_input_data",)),  # Should succeed
            global_limit=Limit(concurrency=2, rps=5.0),
            status=status,
            labeler=simple_labeler,
            retry_settings=RetrySettings(
                max_task_retries=2,
                initial_backoff=0.1,
                max_backoff=0.5,
                is_retriable=lambda e: isinstance(e, (SimulatedAPIError, SimulatedRateLimitError)),
            ),
        )

    results["funcspec_format"] = {
        "results": funcspec_results,
        "call_count": task_call_count,
    }

    # Demo: Manual task control with progress bars
    print("\nDemo: Manual Task Control & Progress Bars")

    async with MultiTaskStatus(
        settings=StatusSettings(transient=False, show_progress=True)
    ) as status:
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

    async with MultiTaskStatus(
        settings=StatusSettings(
            styles=StatusStyles(success_symbol="✨", failure_symbol="💀", retry_symbol="🔥"),
            transient=False,
        )
    ) as status:
        mixed_results = await gather_limited_async(
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


async def text_chunk_processing_demo(total_chunks: int = 50) -> dict[str, Any]:
    """
    Demo for processing text chunks with concurrency 5 and 5 QPS,
    showing chunk progress and first few words in status labels.

    Args:
        total_chunks: Number of chunks to process (default 50)
    """
    print(f"\nDemo: Text Chunk Processing ({total_chunks} chunks, concurrency=5, 5 QPS)")

    # Base text chunks to randomly select from
    base_text_chunks = [
        "The quick brown fox jumps over the lazy dog in the meadow during a beautiful sunny afternoon.",
        "Machine learning algorithms require large datasets to train effectively and produce accurate predictions.",
        "Climate change poses significant challenges to global ecosystems and requires immediate action from governments.",
        "Artificial intelligence is transforming industries by automating complex tasks and improving efficiency.",
        "Space exploration continues to push the boundaries of human knowledge and technological capabilities.",
        "Digital transformation is reshaping how businesses operate and interact with customers.",
        "Renewable energy sources are becoming more cost-effective than fossil fuels.",
    ]

    # Randomly select chunks, allowing duplicates if total_chunks > len(base_text_chunks)
    text_chunks = random.choices(base_text_chunks, k=total_chunks)

    # Simulate processing with some chunks failing initially
    call_counts = {}

    async def process_text_chunk(chunk_text: str, chunk_index: int) -> str:
        """Process a text chunk, with some chunks failing initially to show retries."""
        chunk_key = f"chunk_{chunk_index}"
        call_counts[chunk_key] = call_counts.get(chunk_key, 0) + 1
        current_call = call_counts[chunk_key]

        # Simulate variable processing time
        await asyncio.sleep(random.uniform(0.2, 0.8))

        # Make some chunks fail initially to demonstrate retries
        # Use percentages of total chunks to make failures work with any chunk count
        fail_once_indices = [
            total_chunks // 8,  # ~12.5% through
            total_chunks // 4,  # ~25% through
            total_chunks // 2,  # ~50% through
            3 * total_chunks // 4,  # ~75% through
        ]
        fail_twice_index = total_chunks - 5  # Near the end

        should_fail = False
        if chunk_index in fail_once_indices and current_call == 1:
            should_fail = True
        elif chunk_index == fail_twice_index and current_call <= 2:
            should_fail = True

        if should_fail:
            if chunk_index == 30:
                raise SimulatedRateLimitError(
                    f"Rate limit exceeded processing chunk {chunk_index + 1}"
                )
            else:
                raise SimulatedAPIError(f"Temporary processing error for chunk {chunk_index + 1}")

        # Return processed result
        word_count = len(chunk_text.split())
        return f"processed_chunk_{chunk_index + 1}_{word_count}_words"

    def chunk_labeler(i: int, spec: Any) -> str:
        """Custom labeler showing chunk number and first few words."""
        if isinstance(spec, FuncTask) and spec.args:
            chunk_text = spec.args[0]  # First arg is the chunk text
            chunk_index = spec.args[1]  # Second arg is the chunk index

            # Get first few words (up to 4 words or 30 chars)
            words = chunk_text.split()[:4]
            preview = " ".join(words)
            if len(preview) > 30:
                preview = preview[:27] + "..."

            return f'Chunk {chunk_index + 1}/{total_chunks}: "{preview}..."'

        # Fallback
        return f"Chunk {i + 1}/{total_chunks}"

    # Create FuncTask specs for all chunks
    chunk_specs = [
        FuncTask(process_text_chunk, (chunk_text, i)) for i, chunk_text in enumerate(text_chunks)
    ]

    async with MultiTaskStatus(settings=StatusSettings(transient=False)) as status:
        chunk_results = await gather_limited_async(
            *chunk_specs,
            global_limit=Limit(concurrency=5, rps=5.0),  # Your specified limits
            status=status,
            labeler=chunk_labeler,
            retry_settings=RetrySettings(
                max_task_retries=3,
                max_total_retries=20,  # Reasonable global limit
                initial_backoff=0.2,
                max_backoff=2.0,
                backoff_factor=1.5,
                is_retriable=lambda e: isinstance(e, (SimulatedAPIError, SimulatedRateLimitError)),
            ),
        )

    # Analyze results
    successful_chunks = [r for r in chunk_results if r.startswith("processed_chunk_")]
    failed_chunks = [r for r in chunk_results if not r.startswith("processed_chunk_")]

    total_calls = sum(call_counts.values())
    total_retries = total_calls - len(text_chunks)  # Original calls vs retries

    results = {
        "total_chunks": len(text_chunks),
        "successful_chunks": len(successful_chunks),
        "failed_chunks": len(failed_chunks),
        "total_calls": total_calls,
        "total_retries": total_retries,
        "call_counts": call_counts.copy(),
        "sample_results": chunk_results[:5],  # First 5 results for verification
    }

    print(f"Processed {len(successful_chunks)}/{len(text_chunks)} chunks successfully")
    print(
        f"Total API calls: {total_calls} (original: {len(text_chunks)}, retries: {total_retries})"
    )

    return results


@enable_if("integration")
def test_comprehensive_task_status_demo():
    """Simple pytest wrapper for the demo with basic sanity checks."""

    # Run the demo
    demo_results = asyncio.run(task_status_demo())

    # Basic sanity checks
    assert "api_calls" in demo_results
    assert "sync_tasks" in demo_results
    assert "funcspec_format" in demo_results
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

    # Check FuncSpec format demo
    funcspec_data = demo_results["funcspec_format"]
    assert len(funcspec_data["results"]) == 3
    # Verify results contain expected patterns
    results = funcspec_data["results"]
    assert all("processed_" in result for result in results)
    assert funcspec_data["call_count"] >= 3  # At least one call per task, plus potential retries

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


@enable_if("integration")
def test_text_chunk_processing_demo():
    """Test the text chunk processing demo with default 50 chunks."""

    # Run the chunk processing demo with default 50 chunks
    chunk_results = asyncio.run(text_chunk_processing_demo())

    # Verify basic structure
    assert "total_chunks" in chunk_results
    assert "successful_chunks" in chunk_results
    assert "failed_chunks" in chunk_results
    assert "total_calls" in chunk_results
    assert "total_retries" in chunk_results
    assert "call_counts" in chunk_results
    assert "sample_results" in chunk_results

    # Check that we processed 50 chunks by default
    total_chunks = chunk_results["total_chunks"]
    assert total_chunks == 50

    # All chunks should succeed (after retries)
    assert chunk_results["successful_chunks"] == total_chunks
    assert chunk_results["failed_chunks"] == 0

    # Calculate expected failure indices based on the formula in the demo
    fail_once_indices = [
        total_chunks // 8,  # ~12.5% through
        total_chunks // 4,  # ~25% through
        total_chunks // 2,  # ~50% through
        3 * total_chunks // 4,  # ~75% through
    ]
    fail_twice_index = total_chunks - 5  # Near the end

    # Should have some retries (4 chunks retry once, 1 chunk retries twice)
    expected_retries = len(fail_once_indices) + 2  # 4 single retries + 2 double retries = 6
    assert chunk_results["total_retries"] == expected_retries
    assert chunk_results["total_calls"] == total_chunks + expected_retries

    # Verify specific retry counts for chunks that should fail initially
    call_counts = chunk_results["call_counts"]
    for idx in fail_once_indices:
        assert call_counts[f"chunk_{idx}"] == 2  # Failed once, succeeded on retry
    assert call_counts[f"chunk_{fail_twice_index}"] == 3  # Failed twice, succeeded on third try

    # Check sample results format
    sample_results = chunk_results["sample_results"]
    assert len(sample_results) == 5
    for result in sample_results:
        assert result.startswith("processed_chunk_")
        assert "_words" in result

    print("Text chunk processing demo test passed!")


if __name__ == "__main__":
    # Run both demos
    asyncio.run(task_status_demo())
    asyncio.run(text_chunk_processing_demo())
