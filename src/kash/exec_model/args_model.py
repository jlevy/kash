from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from kash.utils.common.url import Locator

CommandArg = Locator | str
"""
An argument to a command or action. Will be formatted as a string but
may represent a string value, URL, path, store path, etc.
"""


class ArgType(Enum):
    """
    The type of an argument.
    """

    Path = "Path"
    StorePath = "StorePath"
    Url = "Url"
    Locator = "Locator"
    str = "str"


@dataclass(frozen=True)
class ArgCount:
    """
    The number of arguments required for a command or action.
    """

    min_args: int | None
    max_args: int | None

    def as_str(self) -> str:
        if self == ArgCount(0, 0):
            return "No arguments"
        elif self.min_args == self.max_args:
            unit = "argument" if self.min_args == 1 else "arguments"
            return f"Exactly {self.min_args} {unit}"
        elif self.max_args is None:
            unit = "argument" if self.min_args == 1 else "arguments"
            return f"{self.min_args} or more {unit}"
        else:
            unit = "argument" if self.max_args == 1 else "arguments"
            return f"{self.min_args} to {self.max_args} {unit}"


ANY_ARGS = ArgCount(0, None)
NO_ARGS = ArgCount(0, 0)
ONE_OR_NO_ARGS = ArgCount(0, 1)
ONE_OR_MORE_ARGS = ArgCount(1, None)
ONE_ARG = ArgCount(1, 1)
TWO_OR_MORE_ARGS = ArgCount(2, None)
TWO_ARGS = ArgCount(2, 2)


@dataclass(frozen=True)
class Signature:
    """
    The signature (list of argument types) of a command or action.
    """

    arg_type: ArgType | list[ArgType]
    arg_count: ArgCount

    @classmethod
    def single_type(cls, arg_type: ArgType, arg_count: ArgCount) -> Signature:
        return cls(arg_type, arg_count)

    @classmethod
    def multi_type(cls, arg_types: list[ArgType]) -> Signature:
        nargs = len(arg_types)
        return cls(arg_types, ArgCount(nargs, nargs)).validate()

    def validate(self) -> Signature:
        if self.arg_count.min_args != self.arg_count.max_args:
            raise ValueError(f"Multi-type argument count must be fixed: {self.arg_count}")
        if isinstance(self.arg_type, list) and len(self.arg_type) != self.arg_count.min_args:
            raise ValueError(
                f"Multi-type argument count must match number of types: {self.arg_count}"
            )
        return self

    def type_str(self) -> str:
        if isinstance(self.arg_type, list):
            return ", ".join(t.value for t in self.arg_type)
        else:
            return self.arg_type.value

    def human_str(self) -> str:
        return f"{self.arg_count.as_str()} of type {self.type_str()}"
