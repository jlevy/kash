from __future__ import annotations

import logging
import sys
from logging import FileHandler, Formatter, LogRecord
from pathlib import Path

from kash.config.settings import LogLevel, LogLevelStr
from kash.config.suppress_warnings import demote_warnings

# Basic logging setup for non-interactive logging, like on a server.
# For richer logging, see logger.py.


class SuppressedWarningsStreamHandler(logging.StreamHandler):
    def emit(self, record: LogRecord):
        demote_warnings(record, level=logging.DEBUG)
        super().emit(record)


def basic_file_handler(path: Path, level: LogLevel | LogLevelStr) -> logging.FileHandler:
    handler = logging.FileHandler(path)
    handler.setLevel(LogLevel.parse(level).value)

    class ThreadIdFormatter(Formatter):
        def format(self, record):
            # Add shortened thread ID as an attribute
            record.thread_short = str(record.thread)[-5:]
            return super().format(record)

    handler.setFormatter(
        ThreadIdFormatter("%(asctime)s %(levelname).1s [T%(thread_short)s] %(name)s - %(message)s")
    )
    return handler


def basic_stderr_handler(level: LogLevel | LogLevelStr) -> logging.StreamHandler:
    handler = SuppressedWarningsStreamHandler(stream=sys.stderr)
    handler.setLevel(LogLevel.parse(level).value)
    handler.setFormatter(Formatter("%(asctime)s %(levelname).1s %(name)s - %(message)s"))
    return handler


def basic_logging_setup(log_path: Path | None, level: LogLevel | LogLevelStr):
    """
    Set up basic logging to a file and to stderr.
    """
    root_logger = logging.getLogger()
    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)

    if log_path:
        file_handler: FileHandler = basic_file_handler(log_path, level)
        root_logger.addHandler(file_handler)

    stderr_handler = basic_stderr_handler(level)
    root_logger.addHandler(stderr_handler)
