from enum import Enum
from functools import cache
from typing import Any


@cache
def setup(rich_logging: bool):
    """
    One-time setup of essential keys, directories, and configs. Idempotent.
    """
    from kash.config.api_keys import load_dotenv_paths
    from kash.config.logger import reload_rich_logging_setup
    from kash.utils.common.stack_traces import add_stacktrace_handler

    if rich_logging:
        reload_rich_logging_setup()

    _lib_setup()

    add_stacktrace_handler()

    load_dotenv_paths()


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
