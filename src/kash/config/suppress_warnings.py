import logging
import warnings
from logging import LogRecord
from typing import Any
from warnings import formatwarning

FILTER_PATTERNS = [
    "deprecated",
    "Deprecation",
    "PydanticDeprecatedSince20",
    "pydantic",
    # "pydub",
]
"""Warning messages to always suppress in console output."""


def should_suppress(message: Any):
    return any(pattern in str(message) for pattern in FILTER_PATTERNS)


def filter_warnings():
    for pattern in FILTER_PATTERNS:
        warnings.filterwarnings("ignore", message=f".*{pattern}.*")
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", category=RuntimeWarning, module="xonsh.tools")

    log = logging.getLogger("warnings")

    def custom_showwarning(message, category, filename, lineno, _file=None, line=None):
        if not should_suppress(message) and not should_suppress(category):
            log.warning(formatwarning(message, category, filename, lineno, line))

    # Override system default, which writes to stderr.
    warnings.showwarning = custom_showwarning


filter_warnings()


# An even more brute force approach if the approach above doesn't work.
def demote_warnings(record: LogRecord, level: int = logging.INFO):
    if record.levelno == logging.WARNING:
        # Check for any warning patterns that we're filtering in filter_warnings
        if should_suppress(record.msg) or should_suppress(record.module):
            record.levelno = level
