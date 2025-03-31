from collections.abc import Callable
from functools import wraps
from typing import TypeVar

from kash.config.logger import get_logger
from kash.config.text_styles import COLOR_ERROR
from kash.shell.output.shell_output import PrintHooks
from kash.utils.errors import NONFATAL_EXCEPTIONS

log = get_logger(__name__)


def summarize_traceback(exception: Exception) -> str:
    exception_str = str(exception)
    lines = exception_str.splitlines()
    exc_type = type(exception).__name__
    return f"{exc_type}: " + "\n".join(
        [
            line
            for line in lines
            if line.strip()
            and not line.lstrip().startswith("Traceback")
            # and not line.lstrip().startswith("File ")
            and not line.lstrip().startswith("The above exception")
            and not line.startswith("    ")
        ]
        + ["\nRun `logs` for details."]
    )


R = TypeVar("R")


def wrap_with_exception_printing(func: Callable[..., R]) -> Callable[[list[str]], R | None]:
    @wraps(func)
    def command(*args) -> R | None:
        try:
            log.info(
                "Command function call: %s(%s)",
                func.__name__,
                (", ".join(str(arg) for arg in args)),
            )
            return func(*args)
        except NONFATAL_EXCEPTIONS as e:
            PrintHooks.nonfatal_exception()
            log.error(f"[{COLOR_ERROR}]Command error:[/{COLOR_ERROR}] %s", summarize_traceback(e))
            log.info("Command error details: %s", e, exc_info=True)
            return None

    return command
