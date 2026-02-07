from __future__ import annotations

import contextvars
import logging
import os
import re
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from functools import cache
from logging import INFO, Formatter, LogRecord
from pathlib import Path
from typing import IO, Any, cast

import rich
from prettyfmt import slugify_snake
from rich._null_file import NULL_FILE
from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme
from strif import AtomicVar, atomic_output_file, new_timestamped_uid
from typing_extensions import override

import kash.config.suppress_warnings  # noqa: F401
from kash.config.logger_basic import basic_file_handler, basic_stderr_handler
from kash.config.settings import (
    LogLevel,
    get_system_logs_dir,
    global_settings,
)
from kash.config.text_styles import (
    EMOJI_ERROR,
    EMOJI_SAVED,
    EMOJI_WARN,
    RICH_STYLES,
    KashHighlighter,
)
from kash.utils.common.stack_traces import current_stack_traces
from kash.utils.common.task_stack import task_stack_prefix_str


@dataclass
class LogSettings:
    log_console_level: LogLevel
    log_file_level: LogLevel

    global_log_dir: Path
    """Global directory for log files."""

    # These directories can change based on the current workspace:
    log_dir: Path
    """Parent of the "logs" directory. Initially the global kash workspace."""

    log_name: str
    """Name of the log file. Typically the workspace name or "workspace" if for the global workspace."""

    log_objects_dir: Path
    log_file_path: Path

    @property
    def is_quiet(self) -> bool:
        return self.log_console_level >= LogLevel.error


LOG_NAME_GLOBAL = "workspace"


def _read_log_settings() -> LogSettings:
    return LogSettings(
        log_console_level=global_settings().console_log_level,
        log_file_level=global_settings().file_log_level,
        global_log_dir=get_system_logs_dir(),
        log_dir=get_system_logs_dir(),
        log_name=LOG_NAME_GLOBAL,
        log_objects_dir=get_system_logs_dir() / "objects" / LOG_NAME_GLOBAL,
        log_file_path=get_system_logs_dir() / f"{LOG_NAME_GLOBAL}.log",
    )


_log_settings: AtomicVar[LogSettings] = AtomicVar(_read_log_settings())

_setup_done = False


def get_log_settings() -> LogSettings:
    """
    Currently active log settings.
    """
    return _log_settings.copy()


def is_console_quiet() -> bool:
    """
    Whether to suppress non-logging console output.
    """
    return global_settings().console_quiet


def make_valid_log_name(name: str) -> str:
    name = str(name).strip().rstrip("/").removesuffix(".log")
    name = re.sub(r"[^\w-]", "_", name)
    return name


console_context_var: contextvars.ContextVar[Console | None] = contextvars.ContextVar(
    "console", default=None
)
"""
Context variable override for Rich console.
"""


@cache
def get_highlighter():
    return KashHighlighter()


@cache
def get_theme():
    return Theme(RICH_STYLES)


def get_console() -> Console:
    """
    Return the Rich global console, unless it is overridden by a
    context-local console.
    """
    return console_context_var.get() or rich.get_console()


def new_console(file: IO[str] | None, record: bool) -> Console:
    """
    Create a new console with the our theme and highlighter.
    Use `get_console()` for the global console.
    """
    return Console(theme=get_theme(), highlighter=get_highlighter(), file=file, record=record)


@contextmanager
def record_console() -> Generator[Console, None, None]:
    """
    Context manager to temporarily override the global console with a context-local
    console that records output.
    """
    console = new_console(file=NULL_FILE, record=True)
    token = console_context_var.set(console)
    try:
        yield console
    finally:
        console_context_var.reset(token)


# TODO: Need this to enforce flushing of stream?
# class FlushingStreamHandler(logging.StreamHandler):
#     def emit(self, record):
#         super().emit(record)
#         self.flush()


_file_handler: logging.FileHandler
_console_handler: logging.Handler


def reset_rich_logging(
    log_root: Path | None = None,
    log_name: str | None = None,
    log_path: Path | None = None,
):
    """
    Set or reset the logging root or log name, if it has changed. None means no change
    and global default values. `log_name` is the name of the log, excluding
    the `.log` extension. If `log_path` is provided, it will be used to infer
    the log root and name.
    """
    _init_rich_logging()
    if log_path:
        if not log_path.parent.exists():
            log_path.parent.mkdir(parents=True, exist_ok=True)
        log_root = log_path.parent
        log_name = log_path.name

    global _log_settings
    with _log_settings.updates() as settings:
        settings.log_dir = log_root or get_system_logs_dir()
        settings.log_name = make_valid_log_name(log_name or LOG_NAME_GLOBAL)
        reload_rich_logging_setup()


def reload_rich_logging_setup():
    """
    Set up or reset logging setup. This is for rich/formatted console logging and
    file logging. For non-interactive logging, use the `logging` module directly.
    Call at initial run and again if log directory changes. Replaces all previous
    loggers and handlers. Can be called to reset with different settings.
    """
    global _setup_done, _log_settings
    with _log_settings.lock:
        new_log_settings = _read_log_settings()
        if not _setup_done or new_log_settings != _log_settings.value:
            _do_logging_setup(new_log_settings)
            _log_settings.set(new_log_settings)
            _setup_done = True

            # get_console().print(
            #     f"Log file ({_log_settings.log_file_level.name}): "
            #     f"{fmt_path(_log_settings.log_file_path.absolute(), resolve=False)}"
            # )


@cache
def _init_rich_logging():
    """
    One-time idempotent setup of rich logging.
    """
    rich.reconfigure(theme=get_theme(), highlighter=get_highlighter())

    logging.setLoggerClass(CustomLogger)

    reload_rich_logging_setup()


def _do_logging_setup(log_settings: LogSettings):
    from kash.config.suppress_warnings import demote_warnings, filter_warnings

    filter_warnings()

    os.makedirs(log_settings.log_dir, exist_ok=True)
    os.makedirs(log_settings.log_objects_dir, exist_ok=True)

    # Verbose logging to file, important logging to console.
    global _file_handler
    _file_handler = basic_file_handler(log_settings.log_file_path, log_settings.log_file_level)

    class PrefixedRichHandler(RichHandler):
        def emit(self, record: LogRecord):
            demote_warnings(record)
            # Can add an extra indent to differentiate logs but it's a little messier looking.
            # record.msg = EMOJI_MSG_INDENT + record.msg
            super().emit(record)

    global _console_handler

    # Use the Rich stdout handler only on terminals, stderr for servers or non-interactive use.
    if get_console().is_terminal:
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
    else:
        _console_handler = basic_stderr_handler(log_settings.log_console_level)

    # Manually adjust logging for a few packages, removing previous verbose default handlers.
    # Set root logger to most permissive level so handlers can do the filtering
    root_level = min(log_settings.log_console_level.value, log_settings.log_file_level.value)
    log_levels = {
        None: root_level,
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
    if emojis:
        emojis += " "
    return "".join(filter(None, [prefix, emojis, line]))


def prefix_args(
    msg: object, *other_args: object, emoji: str = "", warn_emoji: str = ""
) -> tuple[str, *tuple[object, ...]]:
    """Prefixes the string representation of msg and returns it with other_args."""
    prefixed_msg = prefix(str(msg), emoji, warn_emoji)
    return (prefixed_msg,) + other_args


class CustomLogger(logging.Logger):
    """
    Custom logger to add an additional "message" log level (useful for user-facing
    messages that should appear even if log level is set to warning), add custom
    prefixing, and allow saving objects.
    """

    @override
    def debug(self, msg: object, *args: object, **kwargs: Any) -> None:
        super().debug(*prefix_args(msg, *args), **kwargs)

    @override
    def info(self, msg: object, *args: object, **kwargs: Any) -> None:
        super().info(*prefix_args(msg, *args), **kwargs)

    @override
    def warning(self, msg: object, *args: object, **kwargs: Any) -> None:
        super().warning(*prefix_args(msg, *args, warn_emoji=EMOJI_WARN), **kwargs)

    @override
    def error(self, msg: object, *args: object, **kwargs: Any) -> None:
        super().error(*prefix_args(msg, *args, warn_emoji=EMOJI_ERROR), **kwargs)

    def log_at(self, level: LogLevel, *args: object, **kwargs: Any) -> None:
        getattr(self, level.name)(*args, **kwargs)

    def message(self, msg: object, *args: object, **kwargs: Any) -> None:
        """
        An informative message that should appear even if log level is set to warning.
        """
        super().warning(*prefix_args(msg, *args), **kwargs)

    def save_object(
        self,
        description: str,
        prefix_slug: str | None,
        obj: Any,
        level: LogLevel = LogLevel.info,
        file_ext: str = "txt",
    ) -> None:
        """
        Save an object to a file in the log directory. Useful for details too large to
        log normally but useful for debugging.
        """
        global _log_settings
        prefix = prefix_slug + "." if prefix_slug else ""
        filename = (
            f"{prefix}{slugify_snake(description)}.{new_timestamped_uid()}.{file_ext.lstrip('.')}"
        )
        path = _log_settings.copy().log_objects_dir / filename
        with atomic_output_file(path, make_parents=True) as tmp_filename:
            if isinstance(obj, bytes):
                with open(tmp_filename, "wb") as f:
                    f.write(obj)
            else:
                with open(tmp_filename, "w") as f:
                    f.write(str(obj))

        self.log_at(level, "%s %s saved: %s", EMOJI_SAVED, description, path)

    def dump_stack(self, all_threads: bool = True, level: LogLevel = LogLevel.info) -> None:
        self.log_at(level, "Stack trace dump:\n%s", current_stack_traces(all_threads))

    def __repr__(self):
        level = logging.getLevelName(self.getEffectiveLevel())
        return (
            f"<CustomLogger: name={self.name}, level={level}, handlers={self.handlers}, "
            f"propagate={self.propagate}, parent={self.parent}, disabled={self.disabled})>"
        )


def get_logger(name: str) -> CustomLogger:
    """
    Get a logger that's compatible with system logging but has our additional custom
    methods.
    """
    _init_rich_logging()
    logger = logging.getLogger(name)
    # print("Logger is", logger)
    return cast(CustomLogger, logger)


def get_log_file_stream():
    return _file_handler.stream
