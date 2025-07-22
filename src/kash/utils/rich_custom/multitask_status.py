from __future__ import annotations

import asyncio
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from types import TracebackType
from typing import TYPE_CHECKING, Any, TypeVar

from strif import abbrev_str, single_line
from typing_extensions import override

if TYPE_CHECKING:
    from rich.progress import ProgressColumn

from rich.console import Console, RenderableType
from rich.progress import BarColumn, Progress, ProgressColumn, Task, TaskID
from rich.spinner import Spinner
from rich.text import Text

from kash.config.unified_live import get_unified_live
from kash.utils.api_utils.progress_protocol import (
    EMOJI_FAILURE,
    EMOJI_RETRY,
    EMOJI_SKIP,
    EMOJI_SUCCESS,
    EMOJI_WAITING,
    TaskInfo,
    TaskState,
    TaskSummary,
)

T = TypeVar("T")

# Spinner configuration
SPINNER_NAME = "dots8Bit"


@dataclass(frozen=True)
class StatusStyles:
    """
    All emojis and styles used in TaskStatus display.
    Centralized for easy customization and consistency.
    """

    # Emoji symbols
    success_symbol: str = EMOJI_SUCCESS
    failure_symbol: str = EMOJI_FAILURE
    skip_symbol: str = EMOJI_SKIP
    retry_symbol: str = EMOJI_RETRY
    wait_symbol: str = EMOJI_WAITING

    # Status styles
    retry_style: str = "red"
    success_style: str = "green"
    failure_style: str = "red"
    skip_style: str = "yellow"
    running_style: str = "blue"
    waiting_style: str = "yellow"
    error_style: str = "dim red"

    # Progress bar styles
    progress_complete_style: str = "green"


# Default styles instance
DEFAULT_STYLES = StatusStyles()

# Display symbols
RUNNING_SYMBOL = ""

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
    styles: StatusStyles = DEFAULT_STYLES


class SpinnerStatusColumn(ProgressColumn):
    """
    Column showing spinner when running, status symbol when complete (same width).
    """

    def __init__(
        self,
        *,
        spinner_name: str = SPINNER_NAME,
        styles: StatusStyles = DEFAULT_STYLES,
    ):
        super().__init__()
        self.spinner: Spinner = Spinner(spinner_name)
        self.styles = styles

        # Calculate fixed width for consistent column sizing, adding 2 for padding (space on each side)
        self.column_width: int = max(
            _get_spinner_width(spinner_name) + 2,
            len(styles.success_symbol),
            len(styles.failure_symbol),
            len(styles.skip_symbol),
            len(styles.wait_symbol),
        )

    @override
    def render(self, task: Task) -> Text:
        """Render spinner when running, status symbol when complete."""
        # Get task info from fields
        task_info: TaskInfo | None = task.fields.get("task_info")
        if not task_info or task_info.state == TaskState.QUEUED:
            return Text(" " * self.column_width)

        if task_info.state == TaskState.COMPLETED:
            text = Text(self.styles.success_symbol, style=self.styles.success_style)
        elif task_info.state == TaskState.FAILED:
            text = Text(self.styles.failure_symbol, style=self.styles.failure_style)
        elif task_info.state == TaskState.SKIPPED:
            text = Text(self.styles.skip_symbol, style=self.styles.skip_style)
        elif task_info.state == TaskState.WAITING:
            text = Text(self.styles.wait_symbol, style=self.styles.waiting_style)
        elif task_info.state == TaskState.RUNNING:
            # Running: show spinner with padding
            spinner_result = self.spinner.render(task.get_time())
            if isinstance(spinner_result, Text):
                text = Text(" ") + spinner_result + Text(" ")
            else:
                text = Text(" " + str(spinner_result) + " ")
        else:
            # Should not happen, but return empty space
            return Text(" " * self.column_width)

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
        styles: StatusStyles = DEFAULT_STYLES,
        min_error_length: int = 20,
    ):
        super().__init__()
        self.styles = styles
        self.min_error_length: int = min_error_length
        self._current_max_length: int = min_error_length

    @override
    def render(self, task: Task) -> Text:
        """Render retry indicators and last error message."""
        # Get task info from fields
        task_info: TaskInfo | None = task.fields.get("task_info")
        if not task_info or task_info.retry_count == 0:
            return Text("")

        text = Text()

        # Add retry indicators (red dots for each failure)
        retry_text = self.styles.retry_symbol * task_info.retry_count
        text.append(retry_text, style=self.styles.retry_style)

        # Add last error message if available
        if task_info.failures:
            text.append(" ")
            last_error = task_info.failures[-1]

            # Ensure single line and truncate to max length
            text.append(
                abbrev_str(single_line(last_error), max_len=self._current_max_length),
                style=self.styles.error_style,
            )

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


class TruncatedLabelColumn(ProgressColumn):
    """
    Column that shows task labels truncated to half console width.
    """

    def __init__(self, console_width: int):
        super().__init__()
        # Reserve half the console width for labels/status messages
        self.max_label_width: int = console_width // 2

    @override
    def render(self, task: Task) -> Text:
        """Render task label truncated to max width."""
        label = task.fields.get("label", "")
        if isinstance(label, str):
            truncated_label = abbrev_str(single_line(label), max_len=self.max_label_width)
            return Text(truncated_label)
        return Text(str(label))


class MultiTaskStatus(AbstractAsyncContextManager):
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
        self._task_info: dict[int, TaskInfo] = {}
        self._next_id: int = 1
        self._rich_task_ids: dict[int, TaskID] = {}  # Map our IDs to Rich Progress IDs

        # Unified live integration
        self._unified_live: Any | None = None  # Reference to the global unified live

        # Calculate spinner width for consistent spacing
        self._spinner_width = _get_spinner_width(SPINNER_NAME)

        # Create columns
        spinner_status_column = SpinnerStatusColumn(
            spinner_name=SPINNER_NAME,
            styles=self.settings.styles,
        )

        error_column = ErrorIndicatorColumn(
            styles=self.settings.styles,
        )

        label_column = TruncatedLabelColumn(console_width=self.console.size.width)

        # Store references to columns so we can update them with console info
        self._error_column = error_column
        self._label_column = label_column

        # Build column layout: Spinner/Status | Label | [Progress] | Error indicators
        columns: list[ProgressColumn] = [
            spinner_status_column,
            label_column,
        ]

        # Add optional progress column
        if self.settings.show_progress:
            # Add a standard progress bar column AND custom display column
            columns.append(
                BarColumn(
                    bar_width=self.settings.progress_width,
                    complete_style=self.settings.styles.progress_complete_style,
                    finished_style=self.settings.styles.progress_complete_style,
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

        # Now that we have console access, update columns with proper max lengths
        self._update_column_widths()

    def _update_column_widths(self) -> None:
        """Update column widths based on console width - half for labels, half for errors."""
        console_width = self.console.size.width

        self._error_column._current_max_length = max(
            self._error_column.min_error_length, console_width // 2
        )

        # Update label column max width (half console width)
        self._label_column.max_label_width = console_width // 2

    @property
    def suppress_logs(self) -> bool:
        """Rich-based tracker manages its own display and suppresses standard logging."""
        return True

    @override
    async def __aenter__(self) -> MultiTaskStatus:
        """Start the live display."""
        # Try to integrate with unified live display

        # Always integrate with unified live display (auto-initialized)
        unified_live = get_unified_live()
        self._unified_live = unified_live
        # Register our progress display with the unified live
        unified_live.set_multitask_display(self._progress)
        return self

    @override
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Stop the live display and show automatic summary if enabled."""
        # Always clean up unified live integration
        if self._unified_live is not None:
            # Remove our display from the unified live
            self._unified_live.set_multitask_display(None)
            self._unified_live = None

        # Show automatic summary if enabled (always print to console now)
        if self.auto_summary:
            summary = self.get_summary()
            self.console.print(summary)

    async def add(self, label: str, steps_total: int | None = None) -> int:
        """
        Add a new task to the display. Task won't appear until start() is called.

        Args:
            label: Human-readable task description
            steps_total: Total steps for progress bar (None for no default bar)

        Returns:
            Task ID for subsequent updates
        """
        async with self._lock:
            # Generate our own task ID: don't add to Rich Progress yet
            task_id: int = self._next_id
            self._next_id += 1

            task_info = TaskInfo(label=label, steps_total=steps_total or 1)
            self._task_info[task_id] = task_info
            return task_id

    async def start(self, task_id: int) -> None:
        """
        Mark task as started (after rate limiting/queuing) and add to Rich display.

        Args:
            task_id: Task ID from add()
        """
        async with self._lock:
            if task_id not in self._task_info:
                return

            task_info = self._task_info[task_id]
            task_info.state = TaskState.RUNNING

            # Now add to Rich Progress display
            rich_task_id = self._progress.add_task(
                "",
                total=task_info.steps_total,
                label=task_info.label,
                task_info=task_info,
                progress_display=None,
            )
            self._rich_task_ids[task_id] = rich_task_id

    async def set_progress_display(self, task_id: int, display: RenderableType) -> None:
        """
        Set custom progress display (percentage, text, etc.).

        Args:
            task_id: Task ID from add()
            display: Any Rich renderable (str, Text, percentage, etc.)
        """
        if not self.settings.show_progress:
            return

        async with self._lock:
            # Only update if task has been started (added to Rich Progress)
            rich_task_id = self._rich_task_ids.get(task_id)
            if rich_task_id is not None:
                self._progress.update(rich_task_id, progress_display=display)

    async def update(
        self,
        task_id: int,
        state: TaskState | None = None,
        *,
        steps_done: int | None = None,
        label: str | None = None,
        error_msg: str | None = None,
    ) -> None:
        """
        Update task progress, label, or record a retry attempt.

        Args:
            task_id: Task ID from add()
            state: New task state (None = no change)
            steps_done: Steps to advance (None = no change)
            label: New label (None = no change)
            error_msg: Error message to record as retry (None = no retry)
        """
        async with self._lock:
            if task_id not in self._task_info:
                return

            task_info = self._task_info[task_id]
            rich_task_id = self._rich_task_ids.get(task_id)

            # Update state if provided
            if state is not None:
                task_info.state = state
                if rich_task_id is not None:
                    self._progress.update(rich_task_id, task_info=task_info)

            # Update label if provided
            if label is not None:
                task_info.label = label
                if rich_task_id is not None:
                    self._progress.update(rich_task_id, label=label, task_info=task_info)

            # Advance progress if provided
            if steps_done is not None and rich_task_id is not None:
                self._progress.advance(rich_task_id, advance=steps_done)

            # Record retry if error message provided
            if error_msg is not None:
                task_info.retry_count += 1
                task_info.failures.append(error_msg)
                if rich_task_id is not None:
                    self._progress.update(rich_task_id, task_info=task_info)

    async def finish(
        self,
        task_id: int,
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
            rich_task_id = self._rich_task_ids.get(task_id)

            if message:
                task_info.failures.append(message)

            # Complete the progress bar and stop spinner
            if rich_task_id is not None:
                total = self._progress.tasks[rich_task_id].total or 1
                self._progress.update(rich_task_id, completed=total, task_info=task_info)
            else:
                # Task was never started, but we still need to add it to show completion
                rich_task_id = self._progress.add_task(
                    "",
                    total=task_info.steps_total,
                    label=task_info.label,
                    completed=task_info.steps_total,
                    task_info=task_info,
                )
                self._rich_task_ids[task_id] = rich_task_id

    def get_task_info(self, task_id: int) -> TaskInfo | None:
        """Get additional task information."""
        return self._task_info.get(task_id)

    def get_task_states(self) -> list[TaskState]:
        """Get list of all task states for custom summary generation."""
        return [info.state for info in self._task_info.values()]

    def get_summary(self) -> str:
        """Generate summary message based on current task states."""
        summary = TaskSummary(task_states=self.get_task_states())
        return f"Tasks done: {summary.summary_str()}"

    @property
    def console_for_output(self) -> Console:
        """Get console instance for additional output above progress."""
        return self._progress.console


## Tests


def test_task_status_basic():
    """Test basic TaskStatus functionality."""
    print("Testing TaskStatus...")

    async def _test_impl():
        async with MultiTaskStatus(
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
        async with MultiTaskStatus(
            settings=StatusSettings(show_progress=True),
        ) as status:
            # Traditional progress bar
            download_task = await status.add("Downloading", steps_total=100)
            for i in range(0, 101, 10):
                await status.update(download_task, steps_done=10)
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
        async with MultiTaskStatus(
            settings=StatusSettings(show_progress=True, transient=True),
        ) as status:
            # Multiple concurrent tasks
            install_task = await status.add("Installing packages", steps_total=50)
            test_task = await status.add("Running tests")
            build_task = await status.add("Building project")
            optional_task = await status.add("Optional feature")

            # Simulate concurrent work
            for i in range(5):
                await status.update(install_task, steps_done=10)
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


def test_task_status_retry_states():
    """Test TaskStatus with retry wait states."""
    print("Testing TaskStatus with retry wait states...")

    async def _test_impl():
        async with MultiTaskStatus(
            settings=StatusSettings(show_progress=False, transient=True),
        ) as status:
            # Task that will demonstrate retry wait state
            retry_task = await status.add("API call with retries")
            await status.start(retry_task)

            # Simulate retry cycle
            await status.update(retry_task, error_msg="Connection timeout", state=TaskState.WAITING)
            await asyncio.sleep(1.0)  # Simulate backoff

            await status.update(retry_task, state=TaskState.RUNNING)
            await asyncio.sleep(0.5)  # Simulate execution

            await status.update(
                retry_task, error_msg="Rate limit exceeded", state=TaskState.WAITING
            )
            await asyncio.sleep(1.0)  # Simulate longer backoff

            await status.update(retry_task, state=TaskState.RUNNING)
            await asyncio.sleep(0.5)  # Simulate final execution

            await status.finish(retry_task, TaskState.COMPLETED)

    asyncio.run(_test_impl())
