from __future__ import annotations

import io
from contextlib import redirect_stdout
from dataclasses import dataclass

from kash.config.logger import get_logger, record_console

log = get_logger(__name__)


@dataclass(frozen=True)
class CapturedOutput:
    """
    Holds captured console and stdout output.
    """

    console_text: str
    stdout_text: str

    @property
    def logs(self) -> str:
        logs = ""
        if self.console_text:
            logs += f"Console:\n{self.console_text}\n\n"
        if self.stdout_text:
            logs += f"Stdout:\n{self.stdout_text}\n\n"
        return logs


class captured_output:
    """
    Context manager for capturing Rich console and stdout output.
    Returns a CapturedOutput instance when exiting the context.
    """

    def __init__(self):
        self._output = None
        self.stdout_buffer = None
        self.console = None
        self.stdout_redirector = None

    def __enter__(self) -> captured_output:
        self.stdout_buffer = io.StringIO()
        self.console = record_console().__enter__()
        self.stdout_redirector = redirect_stdout(self.stdout_buffer)
        self.stdout_redirector.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        console_text = self.console.export_text() if self.console else ""
        stdout_text = self.stdout_buffer.getvalue() if self.stdout_buffer else ""

        # Create output object before cleanup.
        self._output = CapturedOutput(console_text=console_text, stdout_text=stdout_text)

        if console_text:
            log.info("Captured console:\n%s", console_text)
        if stdout_text:
            log.info("Captured stdout:\n%s", stdout_text)

        # Clean up the context managers using stored instances.
        stdout_suppress = True
        if self.stdout_redirector:
            stdout_suppress = self.stdout_redirector.__exit__(exc_type, exc_val, exc_tb)
        console_suppress = True
        if self.console:
            console_suppress = self.console.__exit__(exc_type, exc_val, exc_tb)

        # Propagate exceptions unless suppressed by both handlers.
        return stdout_suppress and console_suppress

    @property
    def output(self) -> CapturedOutput:
        if self._output is None:
            raise RuntimeError("Cannot access output before context manager exits")
        return self._output
