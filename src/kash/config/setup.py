from enum import Enum
from functools import cache
from pathlib import Path
from typing import Any

from kash.config.logger_basic import basic_logging_setup
from kash.config.settings import LogLevel, get_system_config_dir


@cache
def setup(rich_logging: bool, file_log_path: Path | None = None, level: LogLevel = LogLevel.info):
    """
    One-time top-level setup of essential logging, keys, directories, and configs.
    Idempotent.

    If rich_logging is True, then rich logging with warnings only for console use.
    If rich_logging is False, then use basic logging to a file and stderr.
    """
    from kash.config.logger import reload_rich_logging_setup
    from kash.shell.clideps.dotenv_utils import load_dotenv_paths
    from kash.utils.common.stack_traces import add_stacktrace_handler

    if rich_logging:
        reload_rich_logging_setup()
    else:
        basic_logging_setup(file_log_path=file_log_path, level=level)

    _lib_setup()

    add_stacktrace_handler()

    load_dotenv_paths(True, True, get_system_config_dir())


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
