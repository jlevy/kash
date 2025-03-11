import logging
import os
import re
import threading
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from functools import cache
from logging import ERROR, Formatter, INFO
from pathlib import Path
from typing import Any, cast, IO, Optional, Tuple

import rich
from rich import reconfigure
from rich._null_file import NULL_FILE
from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme
from slugify import slugify
from strif import atomic_output_file, new_timestamped_uid
from typing_extensions import override

import kash.config.suppress_warnings  # noqa: F401

from kash.config.logger_basic import basic_file_handler
from kash.config.settings import GLOBAL_KASH_DIR, global_settings, LogLevel
from kash.config.text_styles import (
    EMOJI_ERROR,
    EMOJI_SAVED,
    EMOJI_WARN,
    KashHighlighter,
    RICH_STYLES,
)
from kash.util.stack_traces import current_stack_traces
from kash.util.task_stack import task_stack_prefix_str


@dataclass(frozen=True)
class LogSettings:
    log_console_level: LogLevel
    log_file_level: LogLevel
    log_dir: Path
    log_objects_dir: Path
    log_file_path: Path


_log_base = GLOBAL_KASH_DIR
"""
Parent of the "logs" directory. Initially the global kash data root.
"""

_log_name = "default"
"""
Name of the log file. By default the workspace name or "default" if
for the sandbox.
"""

_log_lock = threading.RLock()


def make_valid_log_name(name: str) -> str:
    name = str(name).strip().rstrip("/").removesuffix(".log")
    name = re.sub(r"[^\w-]", "_", name)
    return name


def _read_log_settings() -> LogSettings:
    global _log_base, _log_name
    return LogSettings(
        log_console_level=global_settings().console_log_level,
        log_file_level=global_settings().file_log_level,
        log_dir=_log_base / "logs",
        log_objects_dir=_log_base / "logs" / "objects" / _log_name,
        log_file_path=_log_base / "logs" / f"{_log_name}.log",
    )


_log_settings: LogSettings = _read_log_settings()

_setup_done = False


def get_log_settings() -> LogSettings:
    """
    Currently active log settings.
    """
    return _log_settings


def reset_log_root(log_root: Optional[Path] = None, log_name: Optional[str] = None):
    """
    Reset the logging root or log name, if it has changed. None means no change
    and global default values.
    """
    global _log_lock, _log_base, _log_name
    with _log_lock:
        _log_base = log_root or GLOBAL_KASH_DIR
        _log_name = make_valid_log_name(log_name or "default")
        reload_rich_logging_setup()


@dataclass
class TlContext(threading.local):
    console: Optional[Console] = None


_tl_context = TlContext()
"""
Thread-local context override for Rich console.
"""


@cache
def get_highlighter():
    return KashHighlighter()


@cache
def get_theme():
    return Theme(RICH_STYLES)


reconfigure(theme=get_theme(), highlighter=get_highlighter())


def get_console() -> Console:
    """
    Return the Rich global console, unless it is overridden by a
    thread-local console.
    """
    return _tl_context.console or rich.get_console()


def new_console(file: Optional[IO[str]], record: bool) -> Console:
    """
    Create a new console with the our theme and highlighter.
    Use `get_console()` for the global console.
    """
    return Console(theme=get_theme(), highlighter=get_highlighter(), file=file, record=record)


@contextmanager
def record_console() -> Generator[Console, None, None]:
    """
    Context manager to temporarily override the global console with a thread-local
    console that records output.
    """
    old_console = _tl_context.console
    console = new_console(file=NULL_FILE, record=True)
    _tl_context.console = console

    try:
        yield console
    finally:
        _tl_context.console = old_console


# TODO: Need this to enforce flushing of stream?
# class FlushingStreamHandler(logging.StreamHandler):
#     def emit(self, record):
#         super().emit(record)
#         self.flush()


_file_handler: logging.FileHandler
_console_handler: RichHandler


def reload_rich_logging_setup():
    """
    Set up or reset logging setup. This is for rich/formatted console logging and
    file logging. For non-interactive logging, use the `logging` module directly.
    Call at initial run and again if log directory changes. Replaces all previous
    loggers and handlers. Can be called to reset with different settings.
    """
    global _log_lock, _log_settings, _setup_done
    with _log_lock:
        new_log_settings = _read_log_settings()
        if not _setup_done or new_log_settings != _log_settings:
            _do_logging_setup(new_log_settings)
            _log_settings = new_log_settings
            _setup_done = True

            # get_console().print(
            #     f"Log file ({_log_settings.log_file_level.name}): "
            #     f"{fmt_path(_log_settings.log_file_path.absolute(), resolve=False)}"
            # )


def _do_logging_setup(log_settings: LogSettings):
    kash.config.suppress_warnings.filter_warnings()

    os.makedirs(log_settings.log_dir, exist_ok=True)
    os.makedirs(log_settings.log_objects_dir, exist_ok=True)

    # Verbose logging to file, important logging to console.
    global _file_handler
    _file_handler = basic_file_handler(log_settings.log_file_path, log_settings.log_file_level)

    class PrefixedRichHandler(RichHandler):
        def emit(self, record):
            # Can add an extra indent to differentiate logs but it's a little messier looking.
            # record.msg = EMOJI_MSG_INDENT + record.msg
            super().emit(record)

    global _console_handler
    _console_handler = PrefixedRichHandler(
        # For now we use the fixed global console for logging.
        # In the future we may want to add a way to have thread-local capture
        # of all system logs.
        console=rich.get_console(),
        level=log_settings.log_console_level.value,
        show_time=False,
        show_path=False,
        show_level=False,
        highlighter=get_highlighter(),
        markup=True,
    )
    _console_handler.setLevel(log_settings.log_console_level.value)
    _console_handler.setFormatter(Formatter("%(message)s"))

    # Manually adjust logging for a few packages, removing previous verbose default handlers.

    try:
        import litellm
        from litellm import _logging  # noqa: F401
    except ImportError:
        pass

    litellm.suppress_debug_info = True  # Suppress overly prominent exception messages.

    log_levels = {
        None: INFO,
        "LiteLLM": INFO,
        "LiteLLM Router": INFO,
        "LiteLLM Proxy": INFO,
    }

    for logger_name, level in log_levels.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)
        logger.propagate = True
        # Remove any existing handlers.
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        logger.addHandler(_console_handler)
        logger.addHandler(_file_handler)


def prefix(line: str, emoji: str = "", warn_emoji: str = "") -> str:
    prefix = task_stack_prefix_str()
    emojis = f"{warn_emoji}{emoji}".strip()
    return " ".join(filter(None, [prefix, emojis, line]))


def prefix_args(args: Tuple[Any], emoji: str = "", warn_emoji: str = "") -> Tuple[Any]:
    if len(args) > 0:
        args = (prefix(str(args[0]), emoji, warn_emoji),) + args[1:]
    return args


class CustomLogger(logging.Logger):
    """
    Custom logger to add an additional "message" log level (useful for user-facing
    messages that should appear even if log level is set to warning), add custom
    prefixing, and allow saving objects.
    """

    @override
    def debug(self, *args, **kwargs):
        super().debug(*prefix_args(args), **kwargs)

    @override
    def info(self, *args, **kwargs):
        super().info(*prefix_args(args), **kwargs)

    @override
    def warning(self, *args, **kwargs):
        super().warning(*prefix_args(args, warn_emoji=EMOJI_WARN), **kwargs)

    @override
    def error(self, *args, **kwargs):
        super().error(*prefix_args(args, warn_emoji=EMOJI_ERROR), **kwargs)

    def log_at(self, level: LogLevel, *args, **kwargs):
        getattr(self, level.name)(*args, **kwargs)

    def message(self, *args, **kwargs):
        """
        An informative message that should appear even if log level is set to warning.
        """
        super().warning(*prefix_args(args), **kwargs)

    def save_object(
        self,
        description: str,
        prefix_slug: Optional[str],
        obj: Any,
        level: LogLevel = LogLevel.info,
        file_ext: str = "txt",
    ):
        """
        Save an object to a file in the log directory. Useful for details too large to
        log normally but useful for debugging.
        """
        global _log_settings
        prefix = prefix_slug + "." if prefix_slug else ""
        filename = (
            f"{prefix}{slugify(description, separator='_')}."
            f"{new_timestamped_uid()}.{file_ext.lstrip('.')}"
        )
        path = _log_settings.log_objects_dir / filename
        with atomic_output_file(path, make_parents=True) as tmp_filename:
            if isinstance(obj, bytes):
                with open(tmp_filename, "wb") as f:
                    f.write(obj)
            else:
                with open(tmp_filename, "w") as f:
                    f.write(str(obj))

        self.log_at(level, "%s %s saved: %s", EMOJI_SAVED, description, path)

    def dump_stack(self, all_threads: bool = True, level: LogLevel = LogLevel.info):
        self.log_at(level, "Stack trace dump:\n%s", current_stack_traces(all_threads))

    def __repr__(self):
        level = logging.getLevelName(self.getEffectiveLevel())
        return (
            f"<CustomLogger: name={self.name}, level={level}, handlers={self.handlers}, "
            f"propagate={self.propagate}, parent={self.parent}, disabled={self.disabled})>"
        )


logging.setLoggerClass(CustomLogger)


reload_rich_logging_setup()


def get_logger(name: str) -> CustomLogger:
    """
    Get a logger that's compatible with system logging but has our additional custom
    methods.
    """
    logger = logging.getLogger(name)
    # print("Logger is", logger)
    return cast(CustomLogger, logger)


def get_log_file_stream():
    return _file_handler.stream
