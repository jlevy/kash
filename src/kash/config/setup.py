from functools import cache
from pathlib import Path

from clideps.env_vars.dotenv_utils import load_dotenv_paths

from kash.config.logger import reset_rich_logging
from kash.config.logger_basic import basic_logging_setup
from kash.config.settings import (
    LogLevel,
    LogLevelStr,
    atomic_global_settings,
    configure_ws_and_settings,
    global_settings,
)


@cache
def kash_setup(
    *,
    rich_logging: bool,
    kash_ws_root: Path | None = None,
    log_path: Path | None = None,
    log_level: LogLevel | LogLevelStr | None = None,
    console_log_level: LogLevel | LogLevelStr | None = None,
    console_quiet: bool | None = None,
):
    """
    One-time top-level setup of essential logging, keys, directories, and configs.
    Idempotent.

    Can call this if embedding kash in another app.
    Can be used to set the global default workspace and logs directory
    and/or the default log file.

    Basic logging is to the specified log file.
    If enabled, rich logging is to the console as well.

    By default console is "warning" level but can be controlled with
    the `console_log_level` parameter.
    All console/shell output can be suppressed with `console_quiet`. By default
    console is quiet if `console_log_level` is "error" or higher.
    """
    from kash.utils.common.stack_traces import add_stacktrace_handler

    add_stacktrace_handler()

    # Settings may depend on environment variables, so load them first.
    load_dotenv_paths(True, True, global_settings().system_config_dir)

    # Then configure the workspace and settings before finalizing logging.
    if kash_ws_root:
        configure_ws_and_settings(kash_ws_root)

    # Now set up logging, as it might depend on workspace root.
    log_level = LogLevel.parse(log_level) if log_level else LogLevel.info

    if rich_logging:
        # These settings are only used for rich logging.
        console_log_level = (
            LogLevel.parse(console_log_level) if console_log_level else LogLevel.warning
        )
        console_quiet = (
            console_quiet if console_quiet is not None else console_log_level >= LogLevel.error
        )

        with atomic_global_settings().updates() as settings:
            settings.console_log_level = console_log_level
            settings.file_log_level = log_level
            settings.console_quiet = console_quiet
        reset_rich_logging(log_path=log_path)
    else:
        basic_logging_setup(log_path=log_path, level=log_level)

    _lib_setup()


def _lib_setup():
    from sidematter_format import register_default_yaml_representers

    register_default_yaml_representers()
