from __future__ import annotations

from typing import Any

from pydantic.dataclasses import dataclass

from kash.model.paths_model import StorePath
from kash.utils.common.format_utils import fmt_loc
from kash.utils.common.parse_key_vals import format_key_value
from kash.utils.common.parse_shell_args import shell_quote


@dataclass(frozen=True)
class OperationSummary:
    """
    Brief version of an operation that was performed on an item. We could include a history
    of the full Operations but that seems like a cumbersome amount of metadata, so just
    keeping the action name for now.
    """

    action_name: str


@dataclass(frozen=True)
class Input:
    """
    An input to an operation, which may include a hash fingerprint.
    """

    # TODO: May want to support Locators or other inputs besides StorePaths.
    path: StorePath
    hash: str | None = None

    @classmethod
    def parse(cls, input_str: str) -> Input:
        """
        Parse an Input string in the format `some/path/filename.ext@sha1:hash` or
        `@some/path/filename.ext@sha1:hash`, with a store path and a hash.
        """
        parts = input_str.rsplit("@", 1)
        if len(parts) == 2:
            path, hash = parts
            return cls(path=StorePath(path), hash=hash)
        else:
            return cls(path=StorePath(input_str), hash=None)

    def path_and_hash(self):
        return f"{fmt_loc(self.path)}@{self.hash}"

    # Inputs are equal if the hashes match (even if the paths have changed).

    def __hash__(self):
        return hash(self.hash) if self.hash else object.__hash__(self)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Input):
            return NotImplemented
        if self.hash and other.hash:
            return self.hash == other.hash
        if not self.hash and not other.hash:
            return self.path == other.path
        return False

    def __str__(self):
        return self.path_and_hash()


@dataclass(frozen=True)
class Operation:
    """
    A single operation that was performed, i.e. the name of an action together with all the
    inputs supplied to that action.
    """

    action_name: str
    arguments: list[Input]
    options: dict[str, str]

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Operation:
        action_name = d["action_name"]
        arguments = [Input.parse(input_str) for input_str in d.get("arguments", [])]
        return cls(action_name=action_name, arguments=arguments, options=d.get("options", {}))

    def as_dict(self):
        d: dict[str, Any] = {
            "action_name": self.action_name,
        }

        if self.arguments:
            d["arguments"] = [arg.path_and_hash() for arg in self.arguments]
        if self.options:
            d["options"] = self.options

        return d

    def summary(self) -> OperationSummary:
        return OperationSummary(self.action_name)

    def quoted_args(self):
        return [shell_quote(str(arg.path)) for arg in self.arguments]

    def hashed_args(self):
        return [arg.path_and_hash() for arg in self.arguments]

    def quoted_options(self):
        return [f"--{k}={shell_quote(str(v))}" for k, v in self.options.items()]

    def command_line(self, with_options=True):
        cmd = f"{self.action_name}"

        all_args = []
        if with_options:
            all_args += self.quoted_options()
        all_args += self.quoted_args()
        if all_args:
            cmd += " " + " ".join(all_args)

        return cmd

    def as_str(self):
        args_str = ",".join(self.hashed_args())
        options_str = ",".join(
            format_key_value(k, v, value_formatter=shell_quote) for k, v in self.options.items()
        )
        if options_str:
            options_str = ";" + options_str
        return self.action_name + "(" + args_str + options_str + ")"

    def __str__(self):
        return f"Operation({self.command_line()})"


# Just a nicety to help with sorting these keys when serializing to YAML.
OPERATION_FIELDS = ["action_name", "arguments"]


@dataclass(frozen=True)
class Source:
    """
    A source of an output item describes where the output came from, i.e. the action,
    its inputs, and which output from that action that it is.
    """

    operation: Operation
    """The operation that produced the output."""

    output_num: int
    """If the action produces multiple outputs, this is the index of the output that was used."""

    cacheable: bool = True
    """
    If False, the output is not cacheable, i.e. it relied on something external, like
    input from a user.
    """

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Source:
        return cls(
            operation=Operation.from_dict(d["operation"]),
            output_num=d["output_num"],
            cacheable=d.get("cacheable", True),
        )

    def as_dict(self):
        return {
            "operation": self.operation.as_dict(),
            "output_num": self.output_num,
            "cacheable": self.cacheable,
        }

    def as_str(self):
        return f"{self.operation.as_str()}[{self.output_num}]"

    def __str__(self):
        return self.as_str()
