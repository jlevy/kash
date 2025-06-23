from __future__ import annotations

import asyncio
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from types import TracebackType
from typing import TYPE_CHECKING, TypeVar

from typing_extensions import override

if TYPE_CHECKING:
    from rich.progress import ProgressColumn

from rich.console import Console, RenderableType
from rich.progress import BarColumn, Progress, ProgressColumn, Task, TaskID, TextColumn
from rich.spinner import Spinner
from rich.text import Text

from kash.utils.api_utils.progress_protocol import (
    EMOJI_FAILURE,
    EMOJI_RETRY,
    EMOJI_SKIP,
    EMOJI_SUCCESS,
    SPINNER_NAME,
    TaskInfo,
    TaskState,
    generate_task_summary,
)

T = TypeVar("T")

# Display symbols
RUNNING_SYMBOL = ""

# Display styles
RETRY_STYLE = "red"
SUCCESS_STYLE = "green"
FAILURE_STYLE = "red"
SKIP_STYLE = "yellow"
RUNNING_STYLE = "blue"

# Layout constants
DEFAULT_LABEL_WIDTH = 40
DEFAULT_PROGRESS_WIDTH = 20


# Calculate spinner width to maintain column alignment
def _get_spinner_width(spinner_name: str) -> int:
    """Calculate the maximum width of a spinner's frames."""
    spinner = Spinner(spinner_name)
    return max(len(frame) for frame in spinner.frames)


# Test message symbols
TEST_SUCCESS_PREFIX = EMOJI_SUCCESS
TEST_COMPLETION_MESSAGE = f"{EMOJI_SUCCESS} All operations completed successfully"


@dataclass(frozen=True)
class StatusSettings:
    """
    Configuration settings for TaskStatus display appearance and behavior.

    Contains all display and styling options that control how the task status
    interface appears and behaves, excluding runtime state like console and
    final message.
    """

    show_progress: bool = False
    progress_width: int = DEFAULT_PROGRESS_WIDTH
    label_width: int = DEFAULT_LABEL_WIDTH
    transient: bool = True
    refresh_per_second: float = 10
    success_symbol: str = EMOJI_SUCCESS
    failure_symbol: str = EMOJI_FAILURE
    skip_symbol: str = EMOJI_SKIP
    retry_symbol: str = EMOJI_RETRY
    retry_style: str = RETRY_STYLE
    success_style: str = SUCCESS_STYLE
    failure_style: str = FAILURE_STYLE
    skip_style: str = "yellow"


class SpinnerStatusColumn(ProgressColumn):
    """
    Column showing spinner when running, status symbol when complete (same width).
    """

    def __init__(
        self,
        *,
        spinner_name: str = SPINNER_NAME,
        success_symbol: str = EMOJI_SUCCESS,
        failure_symbol: str = EMOJI_FAILURE,
        skip_symbol: str = EMOJI_SKIP,
        success_style: str = SUCCESS_STYLE,
        failure_style: str = FAILURE_STYLE,
        skip_style: str = "yellow",
    ):
        super().__init__()
        self.spinner: Spinner = Spinner(spinner_name)
        self.success_symbol: str = success_symbol
        self.failure_symbol: str = failure_symbol
        self.skip_symbol: str = skip_symbol
        self.success_style: str = success_style
        self.failure_style: str = failure_style
        self.skip_style: str = skip_style

        # Calculate fixed width for consistent column sizing
        self.column_width: int = max(
            _get_spinner_width(spinner_name),
            len(success_symbol),
            len(failure_symbol),
            len(skip_symbol),
        )

    @override
    def render(self, task: Task) -> Text:
        """Render spinner when running, status symbol when complete."""
        # Get task info from fields
        task_info: TaskInfo | None = task.fields.get("task_info")
        if not task_info:
            return Text(" " * self.column_width)

            # Show appropriate content based on state
        if task_info.state == TaskState.COMPLETED:
            text = Text(self.success_symbol, style=self.success_style)
        elif task_info.state == TaskState.FAILED:
            text = Text(self.failure_symbol, style=self.failure_style)
        elif task_info.state == TaskState.SKIPPED:
            text = Text(self.skip_symbol, style=self.skip_style)
        else:
            # Running - show spinner
            spinner_result = self.spinner.render(task.get_time())
            # Ensure we have a Text object
            if isinstance(spinner_result, Text):
                text = spinner_result
            else:
                text = Text(str(spinner_result))

        # Ensure consistent width
        current_len = len(text.plain)
        if current_len < self.column_width:
            text.append(" " * (self.column_width - current_len))

        return text


class ErrorIndicatorColumn(ProgressColumn):
    """
    Column showing retry indicators and error messages.
    """

    def __init__(
        self,
        *,
        retry_symbol: str = EMOJI_RETRY,
        retry_style: str = RETRY_STYLE,
    ):
        super().__init__()
        self.retry_symbol: str = retry_symbol
        self.retry_style: str = retry_style

    @override
    def render(self, task: Task) -> Text:
        """Render retry indicators and last error message."""
        # Get task info from fields
        task_info: TaskInfo | None = task.fields.get("task_info")
        if not task_info or task_info.retry_count == 0:
            return Text("")

        text = Text()

        # Add retry indicators (red dots for each failure)
        retry_text = self.retry_symbol * task_info.retry_count
        text.append(retry_text, style=self.retry_style)

        # Add last error message if available
        if task_info.failures:
            text.append(" ")
            last_error = task_info.failures[-1]
            text.append(last_error, style="dim red")

        return text


class CustomProgressColumn(ProgressColumn):
    """
    Column that renders arbitrary Rich elements from task fields.
    """

    def __init__(self, field_name: str = "progress_display"):
        super().__init__()
        self.field_name: str = field_name

    @override
    def render(self, task: Task) -> RenderableType:
        """Render custom progress element from task fields."""
        progress_display = task.fields.get(self.field_name)
        return progress_display if progress_display is not None else ""


class TaskStatus(AbstractAsyncContextManager):
    """
    Context manager for live progress status reporting of multiple tasks, a bit like
    uv or pnpm status output when installing packages.

    Layout: [Spinner/Status] [Label] [Progress] [Error indicators + message]

    Features:
    - Fixed-width labels on the left
    - Optional custom progress display (progress bar, percentage, text, etc.)
    - Retry indicators (dots) and status symbols on the right
    - Spinners for active tasks
    - Option to clear display and show final message when done

    Example:
        ```python
        async with TaskStatus(
            show_progress=True,
            transient=True,
            final_message=f"{SUCCESS_SYMBOL} All operations completed"
        ) as status:
            # Standard progress bar
            task1 = await status.add("Downloading", total=100)

            # Custom percentage display
            task2 = await status.add("Processing")
            await status.set_progress_display(task2, "45%")

            # Custom text
            task3 = await status.add("Analyzing")
            await status.set_progress_display(task3, Text("checking...", style="yellow"))
        ```
    """

    def __init__(
        self,
        *,
        console: Console | None = None,
        settings: StatusSettings | None = None,
        auto_summary: bool = True,
    ):
        """
        Initialize TaskStatus display.

        Args:
            console: Rich Console instance, or None for default
            settings: Display configuration settings
            auto_summary: Generate automatic summary message when exiting (if transient=True)
        """
        self.console: Console = console or Console()
        self.settings: StatusSettings = settings or StatusSettings()
        self.auto_summary: bool = auto_summary
        self._lock: asyncio.Lock = asyncio.Lock()
        self._task_info: dict[TaskID, TaskInfo] = {}

        # Create columns
        spinner_status_column = SpinnerStatusColumn(
            spinner_name=SPINNER_NAME,
            success_symbol=self.settings.success_symbol,
            failure_symbol=self.settings.failure_symbol,
            skip_symbol=self.settings.skip_symbol,
            success_style=self.settings.success_style,
            failure_style=self.settings.failure_style,
            skip_style=self.settings.skip_style,
        )

        error_column = ErrorIndicatorColumn(
            retry_symbol=self.settings.retry_symbol,
            retry_style=self.settings.retry_style,
        )

        # Build column layout: Spinner/Status | Label | [Progress] | Error indicators
        columns: list[ProgressColumn] = [
            spinner_status_column,
            TextColumn(
                "[bold blue]{task.fields[label]}",
                justify="left",
            ),
        ]

        # Add optional progress column
        if self.settings.show_progress:
            # Add a standard progress bar column AND custom display column
            columns.append(
                BarColumn(
                    bar_width=self.settings.progress_width,
                    complete_style="green",
                    finished_style="green",
                )
            )
            columns.append(CustomProgressColumn("progress_display"))

        # Add error indicators (retry dots + error messages)
        columns.append(error_column)

        self._progress: Progress = Progress(
            *columns,
            console=self.console,
            transient=self.settings.transient,
            refresh_per_second=self.settings.refresh_per_second,
        )

    @property
    def suppress_logs(self) -> bool:
        """Rich-based tracker manages its own display and suppresses standard logging."""
        return True

    @override
    async def __aenter__(self) -> TaskStatus:
        """Start the live display."""
        self._progress.__enter__()
        return self

    @override
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Stop the live display and show automatic summary if enabled."""
        self._progress.__exit__(exc_type, exc_val, exc_tb)

        # Show automatic summary if enabled
        if self.auto_summary:
            summary = self.get_summary()
            self.console.print(summary)

    async def add(self, label: str, total: int | None = None) -> TaskID:
        """
        Add a new task to the display.

        Args:
            label: Human-readable task description
            total: Total steps for progress bar (None for no default bar)

        Returns:
            Task ID for subsequent updates
        """
        async with self._lock:
            task_info = TaskInfo(label=label)
            task_id = self._progress.add_task(
                "",
                total=total or 1,
                label=label,
                task_info=task_info,
                progress_display=None,
            )
            self._task_info[task_id] = task_info
            return task_id

    async def set_progress_display(self, task_id: TaskID, display: RenderableType) -> None:
        """
        Set custom progress display (percentage, text, etc.).

        Args:
            task_id: Task ID from add()
            display: Any Rich renderable (str, Text, percentage, etc.)
        """
        if not self.settings.show_progress:
            return

        async with self._lock:
            self._progress.update(task_id, progress_display=display)

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
        async with self._lock:
            if task_id not in self._task_info:
                return

            task_info = self._task_info[task_id]

            # Update label if provided
            if label is not None:
                task_info.label = label
                self._progress.update(task_id, label=label, task_info=task_info)

            # Advance progress if provided
            if progress is not None:
                self._progress.advance(task_id, advance=progress)

            # Record retry if error message provided
            if error_msg is not None:
                task_info.retry_count += 1
                task_info.failures.append(error_msg)
                self._progress.update(task_id, task_info=task_info)

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
        async with self._lock:
            if task_id not in self._task_info:
                return

            task_info = self._task_info[task_id]
            task_info.state = state

            if message:
                task_info.failures.append(message)

            # Complete the progress bar and stop spinner
            total = self._progress.tasks[task_id].total or 1
            self._progress.update(task_id, completed=total, task_info=task_info)

    def get_task_info(self, task_id: TaskID) -> TaskInfo | None:
        """Get additional task information."""
        return self._task_info.get(task_id)

    def get_task_states(self) -> list[TaskState]:
        """Get list of all task states for custom summary generation."""
        return [info.state for info in self._task_info.values()]

    def get_summary(self) -> str:
        """Generate summary message based on current task states."""
        return generate_task_summary(self.get_task_states())

    @property
    def console_for_output(self) -> Console:
        """Get console instance for additional output above progress."""
        return self._progress.console


## Tests


def test_task_status_basic():
    """Test basic TaskStatus functionality."""
    print("Testing TaskStatus...")

    async def _test_impl():
        async with TaskStatus(
            settings=StatusSettings(show_progress=False),
        ) as status:
            # Simple task without progress
            task1 = await status.add("Simple task")
            await asyncio.sleep(0.5)
            await status.finish(task1, TaskState.COMPLETED)

            # Task with retries
            retry_task = await status.add("Task with retries")
            await status.update(retry_task, error_msg="Connection timeout")
            await asyncio.sleep(0.5)
            await status.update(retry_task, error_msg="Server error")
            await asyncio.sleep(0.5)
            await status.finish(retry_task, TaskState.COMPLETED)

    asyncio.run(_test_impl())


def test_task_status_with_progress():
    """Test TaskStatus with different progress displays."""
    print("Testing TaskStatus with progress...")

    async def _test_impl():
        async with TaskStatus(
            settings=StatusSettings(show_progress=True),
        ) as status:
            # Traditional progress bar
            download_task = await status.add("Downloading", total=100)
            for i in range(0, 101, 10):
                await status.update(download_task, progress=10)
                await asyncio.sleep(0.1)
            await status.finish(download_task, TaskState.COMPLETED)

            # Custom percentage display
            process_task = await status.add("Processing")
            for i in range(0, 101, 25):
                await status.set_progress_display(process_task, f"{i}%")
                await asyncio.sleep(0.2)
            await status.finish(process_task, TaskState.COMPLETED)

            # Custom text display
            analyze_task = await status.add("Analyzing")
            await status.set_progress_display(
                analyze_task, Text("scanning files...", style="yellow")
            )
            await asyncio.sleep(0.5)
            await status.set_progress_display(analyze_task, Text("building index...", style="cyan"))
            await asyncio.sleep(0.5)
            await status.finish(analyze_task, TaskState.COMPLETED)

    asyncio.run(_test_impl())


def test_task_status_mixed():
    """Test mixed scenarios including skip functionality."""
    print("Testing TaskStatus mixed scenarios...")

    async def _test_impl():
        async with TaskStatus(
            settings=StatusSettings(show_progress=True, transient=True),
        ) as status:
            # Multiple concurrent tasks
            install_task = await status.add("Installing packages", total=50)
            test_task = await status.add("Running tests")
            build_task = await status.add("Building project")
            optional_task = await status.add("Optional feature")

            # Simulate concurrent work
            for i in range(5):
                await status.update(install_task, progress=10)
                await status.set_progress_display(test_task, f"Test {i + 1}/10")
                await status.set_progress_display(build_task, Text(f"Step {i + 1}", style="blue"))
                await asyncio.sleep(0.2)

            await status.finish(install_task, TaskState.COMPLETED)
            await status.update(test_task, error_msg="RateLimitError: Too many requests")
            await status.finish(test_task, TaskState.COMPLETED)
            await status.finish(build_task, TaskState.COMPLETED)

            # Skip the fourth task to demonstrate skip functionality
            await status.finish(optional_task, TaskState.SKIPPED, "Feature disabled in config")

    asyncio.run(_test_impl())
