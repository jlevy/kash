from __future__ import annotations

import atexit
import threading
import time
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field

from rich.console import Console, RenderableType
from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text
from rich.console import Group
from strif import AtomicVar

from kash.config.logger import get_console
from kash.config.text_styles import SPINNER, COLOR_SPINNER


@dataclass
class LiveContent:
    """
    Container for different types of live-updating status content.
    """

    current_status: str | None = None  # Single current status message
    multitask_display: RenderableType | None = None
    custom_content: list[RenderableType] = field(default_factory=list)


class UnifiedLive:
    """
    Unified live display manager that handles all Rich live content in a single Live container.

    This eliminates Rich's one-live-display-at-a-time limitation by
    providing a single Live that all other components render into.

    Layout structure:
    - Status message at the top (single spinner and message)
    - MultiTask progress displays in the middle
    - Custom live content at the bottom
    """

    def __init__(
        self,
        *,
        console: Console | None = None,
        transient: bool = True,
        refresh_per_second: float = 10,
    ):
        self.console = console or get_console()
        self._content = LiveContent()
        self._live = Live(
            console=self.console,
            transient=transient,
            refresh_per_second=refresh_per_second,
        )
        self._is_active = False
        self._lock = threading.RLock()  # Thread safety for mutable state
        self._usage_count = 0  # Track how many things are using this live display

    def start(self) -> None:
        """Start the unified live display."""
        with self._lock:
            if self._is_active:
                return

            try:
                self._live.__enter__()
                self._is_active = True
                self._update_display()
            except Exception:
                # If starting fails, ensure we're in a clean state
                self._is_active = False
                raise

    def stop(self) -> None:
        """Stop the unified live display and restore terminal state."""
        with self._lock:
            if not self._is_active:
                return

            self._is_active = False
            try:
                self._live.__exit__(None, None, None)
            except Exception:
                # Always try to restore terminal state even if Live cleanup fails
                pass
            finally:
                # Force terminal state restoration
                try:
                    # Ensure cursor is visible and terminal is in normal state
                    self.console.show_cursor()
                    if hasattr(self.console, "_buffer"):
                        self.console._buffer.clear()
                except Exception:
                    pass

    def _increment_usage(self) -> None:
        """Increment usage counter (called when entering a context)."""
        with self._lock:
            self._usage_count += 1

    def _decrement_usage(self) -> None:
        """Decrement usage counter and stop if unused (called when exiting a context)."""
        with self._lock:
            self._usage_count = max(0, self._usage_count - 1)
            # Auto-stop if nothing is using it and it has content that would be cleared anyway
            if self._usage_count == 0 and self._content.current_status is None:
                self.stop()

    def set_status(self, message: str | None) -> None:
        """Set the current status message (or None to clear it)."""
        with self._lock:
            self._content.current_status = message
            self._update_display()

    @contextmanager
    def status(self, message: str, *, spinner: str = SPINNER) -> Generator[None, None, None]:  # pyright: ignore[reportUnusedParameter]
        """
        Context manager for showing a status message in this unified live display.

        Args:
            message: Status message to display
            spinner: Spinner type (for future animation support)
        """
        self._increment_usage()
        self.set_status(message)
        try:
            yield
        finally:
            self.set_status(None)
            self._decrement_usage()

    def set_multitask_display(self, display: RenderableType | None) -> None:
        """Set the multitask progress display content."""
        with self._lock:
            self._content.multitask_display = display
            self._update_display()

    def add_custom_content(self, content: RenderableType) -> int:
        """Add custom live content. Returns an ID for later removal."""
        with self._lock:
            self._content.custom_content.append(content)
            self._update_display()
            return len(self._content.custom_content) - 1

    def remove_custom_content(self, content_id: int) -> None:
        """Remove custom content by ID."""
        with self._lock:
            if 0 <= content_id < len(self._content.custom_content):
                del self._content.custom_content[content_id]
                self._update_display()

    def _update_display(self) -> None:
        """Update the live display with current content. Must be called with lock held."""
        if not self._is_active:
            return

        renderables: list[RenderableType] = []

        # Add multitask display at the top
        if self._content.multitask_display is not None:
            renderables.append(self._content.multitask_display)

        # Add custom content in the middle
        renderables.extend(self._content.custom_content)

        # Add current status message with animated spinner at the bottom
        if self._content.current_status is not None:
            from rich.columns import Columns

            spinner = Spinner(SPINNER, style=COLOR_SPINNER)
            status_text = Text(self._content.current_status)

            # Use Columns to display spinner and message side by side
            status_line = Columns([spinner, status_text], padding=(0, 1))
            renderables.append(status_line)

        # Update the live display - use Group to stack vertically
        if renderables:
            self._live.update(Group(*renderables))
        else:
            # Show empty space if no content
            self._live.update("")

    @property
    def is_active(self) -> bool:
        """Check if this unified live is currently active."""
        with self._lock:
            return self._is_active


# Global unified live instance, auto-initialized on first access (thread-safe)
_global_unified_live = AtomicVar[UnifiedLive | None](None)


def _cleanup_unified_live() -> None:
    """Clean up the global unified live display on process exit."""
    current = _global_unified_live.value
    if current is not None:
        current.stop()


# Register cleanup handler for normal exit only
atexit.register(_cleanup_unified_live)


def get_unified_live() -> UnifiedLive:
    """
    Get the global unified live display, auto-initializing if needed.

    Always returns a valid UnifiedLive instance. Creates and starts one
    automatically if none exists yet. Thread-safe using AtomicVar.
    """
    with _global_unified_live.lock:
        if not _global_unified_live:
            live = UnifiedLive()
            live.start()
            _global_unified_live.set(live)

    result = _global_unified_live.value
    assert result
    return result


def has_unified_live() -> bool:
    """Check if there's currently an active unified live display."""
    current = _global_unified_live.value
    return current is not None and current.is_active


@contextmanager
def unified_live_context(
    console: Console | None = None,
) -> Generator[UnifiedLive, None, None]:
    """
    Context manager for working with the unified live display.

    Returns the global unified live instance, creating and starting it if needed.
    The live display continues running after this context exits.
    """
    # Always return the global instance, creating if needed
    live = get_unified_live()

    # Update settings if this is a new instance
    if console is not None:
        live.console = console

    yield live
