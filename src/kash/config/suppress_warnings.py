import logging
import warnings
from logging import LogRecord


def filter_warnings():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", message=".*deprecated.*")
    warnings.filterwarnings("ignore", message=".*Deprecation.*")
    warnings.filterwarnings("ignore", message=".*PydanticDeprecatedSince20.*")
    warnings.filterwarnings("ignore", module="pydub")
    warnings.filterwarnings("ignore", module="pydantic")
    warnings.filterwarnings("ignore", category=RuntimeWarning, module="xonsh.tools")


filter_warnings()


# Doing it even more brute force since the approach above often doesn't work.
def demote_warnings(record: LogRecord):
    if record.levelno == logging.WARNING:
        # Check for any warning patterns that we're filtering in filter_warnings
        if any(
            pattern in record.msg
            for pattern in ["deprecated", "Deprecation", "PydanticDeprecatedSince20"]
        ) or any(module in str(record.pathname) for module in ["pydub", "pydantic", "xonsh.tools"]):
            record.levelno = logging.INFO
