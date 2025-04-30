from enum import Enum
from functools import cache
from pathlib import Path
from typing import Any

from clideps.env_vars.dotenv_utils import load_dotenv_paths

from kash.config.logger import reset_rich_logging
from kash.config.logger_basic import basic_logging_setup
from kash.config.settings import LogLevel, configure_ws_root, global_settings


@cache
def kash_setup(
    *,
    rich_logging: bool,
    kash_ws_root: Path | None = None,
    log_path: Path | None = None,
    level: LogLevel = LogLevel.info,
):
    """
    One-time top-level setup of essential logging, keys, directories, and configs.
    Idempotent.

    Can call this if embedding kash in another app.
    Can be used to set the global default workspace and logs directory
    and/or the default log file.
    If `rich_logging` is True, then rich logging with warnings only for console use.
    If `rich_logging` is False, then use basic logging to a file and stderr.
    """
    from kash.utils.common.stack_traces import add_stacktrace_handler

    if rich_logging:
        reset_rich_logging(log_path=log_path)
    else:
        basic_logging_setup(log_path=log_path, level=level)

    _lib_setup()

    add_stacktrace_handler()

    load_dotenv_paths(True, True, global_settings().system_config_dir)

    if kash_ws_root:
        configure_ws_root(kash_ws_root)


def _lib_setup():
    from frontmatter_format.yaml_util import add_default_yaml_customizer
    from ruamel.yaml import Representer

    def represent_enum(dumper: Representer, data: Enum) -> Any:
        """
        Represent Enums as their values.
        Helps make it easy to serialize enums to YAML everywhere.
        We use the convention of storing enum values as readable strings.
        """
        return dumper.represent_str(data.value)

    add_default_yaml_customizer(
        lambda yaml: yaml.representer.add_multi_representer(Enum, represent_enum)
    )

    # Maybe useful?

    # from pydantic import BaseModel

    # def represent_pydantic(dumper: Representer, data: BaseModel) -> Any:
    #     """Represent Pydantic models as YAML dictionaries."""
    #     return dumper.represent_dict(data.model_dump())

    # add_default_yaml_customizer(
    #     lambda yaml: yaml.representer.add_multi_representer(BaseModel, represent_pydantic)
    # )
