import logging
from logging import FileHandler, Formatter
from pathlib import Path

from kash.config.settings import LogLevel

# Basic logging setup for non-interactive logging, like on a server.
# For richer logging, see logger.py.


def basic_file_handler(path: Path, level: LogLevel) -> logging.FileHandler:
    handler = logging.FileHandler(path)
    handler.setLevel(level.value)
    handler.setFormatter(Formatter("%(asctime)s %(levelname).1s %(name)s - %(message)s"))
    return handler


def basic_stderr_handler(level: LogLevel) -> logging.StreamHandler:
    handler = logging.StreamHandler()
    handler.setLevel(level.value)
    handler.setFormatter(Formatter("%(asctime)s %(levelname).1s %(name)s - %(message)s"))
    return handler


def basic_logging_setup(file_log_path: Path | None, level: LogLevel):
    """
    Set up basic logging to a file and to stderr.
    """
    root_logger = logging.getLogger()
    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)

    if file_log_path:
        file_handler: FileHandler = basic_file_handler(file_log_path, level)
        root_logger.addHandler(file_handler)

    stderr_handler = basic_stderr_handler(level)
    root_logger.addHandler(stderr_handler)
