from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, TypeAlias, TypeVar

T = TypeVar("T")
TaskID = TypeVar("TaskID")

# Generic task spec types for labeler functions
TaskSpec = TypeVar("TaskSpec")
Labeler: TypeAlias = Callable[[int, TaskSpec], str]

# Progress display symbols (consistent with text_styles.py)
EMOJI_SUCCESS = "[✔︎]"
EMOJI_FAILURE = "[✘]"
EMOJI_SKIP = "[-]"
EMOJI_WARN = "[∆]"
EMOJI_RETRY = "▵"

# Spinner configuration
SPINNER_NAME = "dots12"


class TaskState(Enum):
    """Task execution states."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TaskInfo:
    """Track additional task information beyond basic progress."""

    state: TaskState = TaskState.QUEUED
    retry_count: int = 0
    failures: list[str] = field(default_factory=list)
    label: str = ""
    total: int = 1


@dataclass(frozen=True)
class TaskSummary:
    """Summary of task completion states."""

    task_states: list[TaskState]

    @property
    def queued(self) -> int:
        """Number of queued tasks."""
        return sum(1 for state in self.task_states if state == TaskState.QUEUED)

    @property
    def running(self) -> int:
        """Number of running tasks."""
        return sum(1 for state in self.task_states if state == TaskState.RUNNING)

    @property
    def completed(self) -> int:
        """Number of completed tasks."""
        return sum(1 for state in self.task_states if state == TaskState.COMPLETED)

    @property
    def failed(self) -> int:
        """Number of failed tasks."""
        return sum(1 for state in self.task_states if state == TaskState.FAILED)

    @property
    def skipped(self) -> int:
        """Number of skipped tasks."""
        return sum(1 for state in self.task_states if state == TaskState.SKIPPED)

    @property
    def total(self) -> int:
        """Total number of tasks."""
        return len(self.task_states)

    def summary_str(self) -> str:
        """
        Generate summary message based on task completion states.
        """
        if not self.task_states:
            return "No tasks to process"

        if self.completed == self.total:
            return f"All tasks successful: {self.completed}/{self.total} completed"
        elif self.completed + self.skipped == self.total:
            return f"All tasks successful: {self.completed}/{self.total} completed, {self.skipped} skipped"
        elif self.failed == self.total:
            return f"All tasks failed: {self.failed}/{self.total} failed"
        else:
            parts = []
            if self.completed > 0:
                parts.append(f"{self.completed}/{self.total} tasks completed")
            if self.failed > 0:
                parts.append(f"{self.failed} tasks failed")
            if self.skipped > 0:
                parts.append(f"{self.skipped} tasks skipped")
            if self.queued > 0:
                parts.append(f"{self.queued} tasks not yet run")

            if self.queued > 0:
                return "Tasks were interrupted: " + ", ".join(parts)
            else:
                return "Tasks had errors: " + ", ".join(parts)


class ProgressTracker(Protocol[TaskID]):
    """
    Protocol for progress tracking that gather_limited can depend on.

    This allows different implementations (Rich, simple logging, etc.)
    without creating a hard dependency. Uses a simplified update model.
    """

    @property
    def suppress_logs(self) -> bool:
        """
        Whether this tracker handles its own display and should suppress
        standard logging to avoid visual interference.
        """
        ...

    async def add(self, label: str, total: int = 1) -> TaskID:
        """Add a new task to track."""
        ...

    async def start(self, task_id: TaskID) -> None:
        """Mark task as started (after rate limiting/queuing)."""
        ...

    async def update(
        self,
        task_id: TaskID,
        *,
        progress: int | None = None,
        label: str | None = None,
        error_msg: str | None = None,
    ) -> None:
        """
        Update task progress, label, or record a retry attempt.

        Args:
            task_id: Task ID from add()
            progress: Steps to advance (None = no change)
            label: New label (None = no change)
            error_msg: Error message to record as retry (None = no retry)
        """
        ...

    async def finish(
        self,
        task_id: TaskID,
        state: TaskState,
        message: str = "",
    ) -> None:
        """
        Mark task as finished with final state.

        Args:
            task_id: Task ID from add()
            state: Final state (COMPLETED, FAILED, SKIPPED)
            message: Optional completion/error/skip message
        """
        ...


class AsyncProgressContext(Protocol[TaskID]):
    """Protocol for async context manager progress trackers."""

    async def __aenter__(self) -> ProgressTracker[TaskID]:
        """Start progress tracking."""
        ...

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any
    ) -> None:
        """Stop progress tracking."""
        ...


class SimpleProgressTracker:
    """
    Basic progress tracker that logs to console.
    Useful for testing or when Rich is not available.
    """

    def __init__(self, *, verbose: bool = True, print_fn: Callable[[str], None] = print):
        self.verbose = verbose
        self.print_fn = print_fn
        self._next_id = 1
        self._tasks: dict[int, TaskInfo] = {}

    @property
    def suppress_logs(self) -> bool:
        """Console-based tracker works with standard logging."""
        return False

    async def add(self, label: str, total: int = 1) -> int:  # pyright: ignore[reportUnusedParameter]
        task_id = self._next_id
        self._next_id += 1

        self._tasks[task_id] = TaskInfo(label=label)

        if self.verbose:
            self.print_fn(f"Queued: {label}")

        return task_id

    async def start(self, task_id: int) -> None:
        """Mark task as started (after rate limiting/queuing)."""
        task_info = self._tasks.get(task_id)
        if not task_info:
            return

        task_info.state = TaskState.RUNNING

        if self.verbose:
            self.print_fn(f"Started: {task_info.label}")

    async def update(
        self,
        task_id: int,
        *,
        progress: int | None = None,  # pyright: ignore[reportUnusedParameter]
        label: str | None = None,
        error_msg: str | None = None,
    ) -> None:
        task_info = self._tasks.get(task_id)
        if not task_info:
            return

        # Update label if provided
        if label is not None:
            task_info.label = label

        # Record retry if error message provided
        if error_msg is not None:
            task_info.retry_count += 1
            task_info.failures.append(error_msg)

            if self.verbose:
                retry_indicator = EMOJI_RETRY * task_info.retry_count
                self.print_fn(f"Retry {retry_indicator} {task_info.label}: {error_msg}")

    async def finish(
        self,
        task_id: int,
        state: TaskState,
        message: str = "",
    ) -> None:
        task_info = self._tasks.get(task_id)
        if not task_info:
            return

        task_info.state = state

        if self.verbose:
            if state == TaskState.COMPLETED:
                symbol = EMOJI_SUCCESS
            elif state == TaskState.FAILED:
                symbol = EMOJI_FAILURE
            elif state == TaskState.SKIPPED:
                symbol = EMOJI_SKIP
            else:
                symbol = "?"

            retry_info = (
                f" (after {task_info.retry_count} retries)" if task_info.retry_count else ""
            )

            message_info = f": {message}" if message else ""
            self.print_fn(f"{symbol} {task_info.label}{retry_info}{message_info}")


class SimpleProgressContext:
    """
    Simple async context manager for SimpleProgressTracker.
    """

    def __init__(self, *, verbose: bool = True, print_fn: Callable[[str], None] = print):
        self.verbose = verbose
        self.print_fn = print_fn
        self._tracker: SimpleProgressTracker | None = None

    async def __aenter__(self) -> SimpleProgressTracker:
        self._tracker = SimpleProgressTracker(verbose=self.verbose, print_fn=self.print_fn)
        return self._tracker

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any
    ) -> None:
        if self.verbose and self._tracker:
            # Generate automatic summary
            task_states = [info.state for info in self._tracker._tasks.values()]
            summary = TaskSummary(task_states=task_states)
            self.print_fn(summary.summary_str())
