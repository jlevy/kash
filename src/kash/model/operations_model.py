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
    Typically an input is a StorePath, but it could be something else like an in-memory
    item that hasn't been saved yet.
    """

    path: StorePath | None
    hash: str | None = None
    source_info: str | None = None

    @classmethod
    def parse(cls, input_str: str) -> Input:
        """
        Parse an Input string in the format printed by `Input.parseable_str()`.
        """
        if input_str.startswith("[") and input_str.endswith("]"):
            return cls(path=None, hash=None, source_info=input_str[1:-1])
        else:
            parts = input_str.rsplit("@", 1)
            if len(parts) == 2:
                path, hash = parts
                return cls(path=StorePath(path), hash=hash)
            else:
                return cls(path=StorePath(input_str), hash=None)

    def parseable_str(self):
        """
        A readable and parseable string describing the input, typically a hash and a path but
        could be a path without a hash or another info in brackets. Paths may have an `@` at the
        front.

        some/path.txt@sha1:1234567890
        @some/path.txt@sha1:1234567890
        some/path.txt
        [unsaved]
        """
        if self.path and self.hash:
            return f"{fmt_loc(self.path)}@{self.hash}"
        elif self.source_info:
            return f"[{self.source_info}]"
        else:
            return "[input info missing]"

    # Inputs are equal if the hashes match (even if the paths have changed).

    def __hash__(self):
        return hash(self.hash) if self.hash else object.__hash__(self)

    def __eq__(self, other: Any) -> bool:
        """
        Inputs are equal if the hashes match (even if the paths have changed) or if the paths
        are the same. They are *not* equal otherwise, even if the source_info is the same.
        """
        if not isinstance(other, Input):
            return NotImplemented
        if self.hash and other.hash:
            return self.hash == other.hash
        if not self.hash and not other.hash:
            return self.path == other.path
        return False

    def __str__(self):
        return self.parseable_str()


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
            d["arguments"] = [arg.parseable_str() for arg in self.arguments]
        if self.options:
            d["options"] = self.options

        return d

    def summary(self) -> OperationSummary:
        return OperationSummary(self.action_name)

    def quoted_args(self):
        return [shell_quote(str(arg.path)) for arg in self.arguments]

    def hashed_args(self):
        return [arg.parseable_str() for arg in self.arguments]

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
