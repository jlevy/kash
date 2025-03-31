from __future__ import annotations

from collections.abc import Iterable
from dataclasses import field, replace
from enum import Enum
from pathlib import Path
from typing import Any, Generic, TypeAlias, TypeVar

from chopdiff.docs import TextUnit
from prettyfmt import fmt_lines
from pydantic.dataclasses import dataclass
from pydantic.json_schema import JsonSchemaValue

from kash.config.logger import get_logger
from kash.docs.all_docs import DocSelection
from kash.llm_utils import LLM, LLMName
from kash.model.language_list import LANGUAGE_LIST
from kash.utils.common.parse_key_vals import format_key_value
from kash.utils.common.type_utils import instantiate_as_type
from kash.utils.errors import InvalidInput, InvalidParamName

log = get_logger(__name__)


T = TypeVar("T")


@dataclass(frozen=True)
class Param(Generic[T]):
    """
    Describes a settable parameter. This describes the parameter itself (including type and
    default value). It includes the (global) default value for the parameter but not its
    actual value. May be used globally or as an option to a command or action.
    """

    name: str

    description: str | None

    type: type[T]

    default_value: T | None = None
    """
    The default value for the parameter.
    """

    is_explicit: bool = False
    """
    Normally a parameter can have a global or action-specific default value. But if this
    is true, the parameter is like an input that is always explicitly required at runtime
    (like a query string).
    """

    valid_str_values: list[str] | None = None
    """
    If the parameter is a string but has only certain allowed or suggested values,
    list them here. Not necessary for enums, which are handled automatically.
    """

    is_open_ended: bool = False
    """
    If true and `valid_str_values` is set, the parameter can take any string value and
    the `valid_str_values` are suggestions only.
    """

    def __post_init__(self):
        if not self.name or not self.name.replace("_", "").isalnum():
            raise ValueError(f"Not a valid param name: {repr(self.name)}")
        if self.default_value is not None and not isinstance(self.default_value, self.type):
            raise TypeError(
                f"Default value for param `{self.name}` must be an instance of {self.type}: {self.default_value}"
            )

    @property
    def default_value_str(self) -> str | None:
        if self.default_value is None:
            return None
        elif issubclass(self.type, Enum):
            return self.type(self.default_value).name
        else:
            return str(self.default_value)

    @property
    def valid_values(self) -> list[str]:
        if self.valid_str_values:
            return self.valid_str_values
        elif issubclass(self.type, Enum):
            # Use the enum names as the valid values.
            return [e.name for e in self.type]
        else:
            return []  # Any value is allowed.

    def validate_value(self, value: Any) -> None:
        """
        For enum or closed str types, validate that the value is in the list of valid values.
        """
        if self.valid_str_values and not self.is_open_ended and value not in self.valid_str_values:
            raise InvalidInput(
                f"Invalid value for parameter `{self.name}`: {value!r} not in allowed str values: {self.valid_str_values}"
            )
        elif issubclass(self.type, Enum) and value not in self.type:
            raise InvalidInput(
                f"Invalid value for parameter `{self.name}`: {value!r} not in allowed enum values: {list(self.type)}"
            )

    @property
    def full_description(self) -> str:
        desc = self.description or ""
        if desc:
            desc += "\n\n"
        desc += self.valid_and_default_values
        return desc

    @property
    def valid_and_default_values(self) -> str:
        doc_str = ""
        if self.valid_values:
            val_list = ", ".join(f"`{v}`" for v in self.valid_values)
            if self.is_open_ended:
                doc_str += f"Suggested values (open str type {self.type.__name__}): {val_list}"
            else:
                doc_str += f"Allowed values (type {self.type.__name__}): {val_list}"
        if self.default_value:
            if doc_str:
                doc_str += "\n\n"
            doc_str += f"Default value is: `{self.default_value}`"
        return doc_str

    @property
    def is_bool(self) -> bool:
        return issubclass(self.type, bool)

    @property
    def is_path(self) -> bool:
        return issubclass(self.type, Path) or (
            # XXX As a convenience, infer path types from the variable name..
            issubclass(self.type, str) and self.name in ("path", "paths")
        )

    @property
    def shell_prefix(self) -> str:
        if self.is_bool:
            return f"--{self.name}"
        else:
            return f"--{self.name}="

    @property
    def display(self) -> str:
        if self.is_bool:
            return f"{self.shell_prefix}"
        else:
            return f"{self.shell_prefix}VALUE"

    def with_default(self, default: T) -> Param:
        return replace(self, default_value=default)

    def json_schema(self) -> JsonSchemaValue:
        """
        Generate a JSON schema for this parameter.
        """
        schema: JsonSchemaValue = {
            "title": self.name,
            "description": self.description or "",
        }

        if issubclass(self.type, bool):
            schema["type"] = "boolean"
        elif issubclass(self.type, int):
            schema["type"] = "integer"
        elif issubclass(self.type, float):
            schema["type"] = "number"
        elif issubclass(self.type, str):
            schema["type"] = "string"
            if self.valid_str_values and not self.is_open_ended:
                schema["enum"] = self.valid_str_values
        elif issubclass(self.type, Enum):
            # Enums serialized by value.
            schema["type"] = "string"
            schema["enum"] = [e.value for e in self.type]
        else:
            # Default to string for complex types.
            schema["type"] = "string"

        if self.default_value is not None:
            if issubclass(self.type, Enum):
                # Enums serialized by value.
                schema["default"] = self.type(self.default_value).value
            else:
                schema["default"] = self.default_value

        return schema


RawParamValue = str | bool
"""
Serialized string or boolean value for a parameter. May be converted to another type
like an enum. This type is compatible with command-line option values.
"""


ParamDeclarations: TypeAlias = tuple[Param, ...]
"""
A list of parameter declarations, possibly with default values.
"""


# These are the default models for typical use cases.
# The user may override them with parameters.
DEFAULT_CAREFUL_LLM = LLM.o1_preview
DEFAULT_STRUCTURED_LLM = LLM.gpt_4o
DEFAULT_STANDARD_LLM = LLM.claude_3_7_sonnet
DEFAULT_FAST_LLM = LLM.claude_3_5_haiku


# Parameters set globally such as in the workspace.
MODEL_PARAMS: dict[str, Param] = {
    "careful_llm": Param(
        "careful_llm",
        "Default LLM used for complex, unstructured requests (including for the kash assistant).",
        default_value=DEFAULT_CAREFUL_LLM,
        type=LLMName,
        valid_str_values=list(LLM),
        is_open_ended=True,
    ),
    "structured_llm": Param(
        "structured_llm",
        "Default LLM used for complex, structured requests (including for the kash assistant).",
        default_value=DEFAULT_STRUCTURED_LLM,
        type=LLMName,
        valid_str_values=list(LLM),
        is_open_ended=True,
    ),
    "standard_llm": Param(
        "standard_llm",
        "Default LLM used for basic requests (including for the kash assistant).",
        default_value=DEFAULT_STANDARD_LLM,
        type=LLMName,
        valid_str_values=list(LLM),
        is_open_ended=True,
    ),
    "fast_llm": Param(
        "fast_llm",
        "Default LLM used for fast responses (including for the kash assistant).",
        default_value=DEFAULT_FAST_LLM,
        type=LLMName,
        valid_str_values=list(LLM),
        is_open_ended=True,
    ),
}

GLOBAL_PARAMS: dict[str, Param] = {
    **MODEL_PARAMS,
}

# Parameters that are common to all actions.
COMMON_ACTION_PARAMS: dict[str, Param] = {
    "model": Param(
        "model",
        "The name of the LLM.",
        default_value=None,  # Let actions set defaults.
        type=LLMName,
        valid_str_values=list(LLM),
        is_open_ended=True,
    ),
    "language": Param(
        "language",
        "The language of the input audio or text.",
        type=str,
        default_value=None,
        valid_str_values=LANGUAGE_LIST,
    ),
    "chunk_size": Param(
        "chunk_size",
        "For actions that support it, process chunks of what size?",
        default_value=None,
        type=int,
    ),
    "chunk_unit": Param(
        "chunk_unit",
        "For actions that support it, the unit for measuring chunk size.",
        default_value=None,
        type=TextUnit,
    ),
    "query": Param(
        "query",
        "For search actions, the query to use.",
        type=str,
        default_value=None,
        is_explicit=True,
    ),
    "doc_selection": Param(
        "doc_selection",
        "Which kash docs to give the LLM assistant.",
        type=DocSelection,
        default_value=DocSelection.full,
    ),
}

# Extra parameters that are available when an action is invoked from the shell.
# Applies globally to all actions.
RUNTIME_ACTION_PARAMS: dict[str, Param] = {
    "rerun": Param(
        "rerun",
        "Rerun an action that would otherwise be skipped because "
        "it produces an output item that already exists.",
        type=bool,
    ),
}


USER_SETTABLE_PARAMS: dict[str, Param] = {**GLOBAL_PARAMS, **COMMON_ACTION_PARAMS}

ALL_COMMON_PARAMS: dict[str, Param] = {
    **GLOBAL_PARAMS,
    **COMMON_ACTION_PARAMS,
    **RUNTIME_ACTION_PARAMS,
}

HELP_PARAM = Param(
    "help",
    "Show full help for this command or action.",
    type=bool,
)

SHOW_SOURCE_PARAM = Param(
    "show_source",
    "Show the source code for this command or action.",
    type=bool,
)

# Parameters present on all shell commands but not formally options to the
# commands or actions.
COMMON_SHELL_PARAMS: dict[str, Param] = {
    "help": HELP_PARAM,
    "show_source": SHOW_SOURCE_PARAM,
}


def common_param(name: str) -> Param:
    """
    Get a commonly used parameter by name.
    """
    param = ALL_COMMON_PARAMS.get(name)
    if param is None:
        raise InvalidParamName(name)
    return param


def common_params(*names: str) -> tuple[Param, ...]:
    """
    Get a set of commonly used parameters by name.
    """
    return tuple(common_param(name) for name in names)


@dataclass
class RawParamValues:
    """
    A set of raw parameter values in raw (mostly untyped string or bool) format,
    as they are read from the shell.
    """

    values: dict[str, RawParamValue] = field(default_factory=dict)

    def items(self):
        return self.values.items()

    def get_parsed_value(
        self, param_name: str, type: type[T], param_info: dict[str, Param]
    ) -> T | None:
        raw_value = self.values.get(param_name)
        if raw_value is None:
            param = param_info.get(param_name)
            if param:
                return param.default_value
            else:
                raise InvalidParamName(param_name)
        else:
            try:
                return instantiate_as_type(raw_value, type)
            except ValueError as e:
                raise InvalidInput(f"Invalid value for parameter `{param_name}`: {e}") from e

    def parse_all(self, param_info: dict[str, Param]) -> TypedParamValues:
        """
        Convert and validate all raw values to typed values, using the provided parameter info.
        Any extra params in the provided `param_info` are ignored.
        """
        applicable_params = {
            name: param for name, param in param_info.items() if name in self.values.keys()
        }
        if len(applicable_params) != len(self.values):
            raise InvalidInput(
                f"Did not find matching params for the given parameter names: "
                f"{', '.join(repr(k) for k in self.values.keys() - applicable_params.keys())}"
            )

        values = {
            name: self.get_parsed_value(name, param.type, param_info)
            for name, param in applicable_params.items()
        }
        typed_values = TypedParamValues(values=values, params=applicable_params)

        log.info("Raw params: %s", self)
        log.info("Parsed params: %s", typed_values)
        return typed_values

    def as_str(self) -> str:
        if self.items():
            return fmt_lines([format_key_value(name, value) for name, value in self.items()])
        else:
            return fmt_lines(["(no parameters)"])

    def as_str_brief(self):
        return str(self.values)

    def __str__(self):
        return self.as_str_brief()


@dataclass(frozen=True)
class TypedParamValues:
    """
    A set of parameter values in typed format, with parameter info for
    each value.
    """

    values: dict[str, Any] = field(default_factory=dict)
    params: dict[str, Param] = field(default_factory=dict)

    def __post_init__(self):
        if set(self.values.keys()) != set(self.params.keys()):
            raise ValueError(
                f"Parameter names in values and params must match: "
                f"{sorted(self.values.keys())} != {sorted(self.params.keys())}"
            )

    @staticmethod
    def create(values: dict[str, Any], param_info: Iterable[Param]) -> TypedParamValues:
        """
        Create a `TypedParamValues`, checking that all values have corresponding
        param info.
        """
        params = {p.name: p for p in param_info if p.name in values}
        if set(params.keys()) != set(values.keys()):
            raise ValueError(
                f"Missing params for supplied values: values for {sorted(values.keys())} but params for {sorted(params.keys())}"
            )
        return TypedParamValues(values=values, params=params)
