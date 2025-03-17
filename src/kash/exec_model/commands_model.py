from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, field_validator
from strif import single_line

from kash.utils.common.parse_shell_args import (
    StrBoolOptions,
    format_command_str,
    format_options,
    parse_command_str,
    parse_option,
)

if TYPE_CHECKING:
    from kash.model.actions_model import Action


def stringify_non_bool(value: Any) -> str | bool:
    if isinstance(value, bool):
        return value
    else:
        return str(value)


class Command(BaseModel):
    """
    A command that can be run in the shell, saved to history, etc.
    We keep options unparsed in persisted form for convenience with serialization
    and use with LLMs structured outputs.

    Example:
    `transcribe resources/some-file.resource.yml --language=en --rerun`
    is represented as:
    {"name": "transcribe", "args": ["resources/some-file.resource.yml"], "options": ["--language=en", "--rerun"]}

    """

    name: str

    args: list[str]
    """
    The list of arguments, as they appear in string form on the command line.
    """

    options: list[str]
    """
    `options` is a list of options in string format, i.e. `--name=value` for string
    options or `--name` for boolean options.
    """

    @property
    def parsed_options(self) -> StrBoolOptions:
        """
        Return a dictionary of options. Command-line options with values are represented
        with a string value. Command-line options present but without a value are represented
        as a boolean True.
        """
        parsed_options = [parse_option(option) for option in self.options]
        return {k: v for k, v in parsed_options}

    @classmethod
    def from_command_str(cls, command_str: str) -> Command:
        name, args, options = parse_command_str(command_str)
        return cls(name=name, args=args, options=format_options(options))

    @classmethod
    def assemble(
        cls,
        callable: Action | Callable | str,
        args: Iterable[Any] | None = None,
        options: dict[str, Any] | None = None,
    ):
        """
        Assemble a serializable Command from any Action, Callable, or string and
        args and option values. Values can be provided as values or as string values.

        Options that are None or False are dropped as they are interpreted to mean
        omitted optional params or disabled boolean flags.
        """
        from kash.model.actions_model import Action

        if isinstance(callable, Action):
            name = callable.name
        elif isinstance(callable, Callable):
            name = callable.__name__
        elif isinstance(callable, str):
            name = callable
        else:
            raise ValueError(f"Invalid action or command: {callable}")

        if args and None in args:
            raise ValueError("None is not a valid argument value.")

        # Ensure values are stringified.
        str_args: list[str] = []
        if args:
            str_args = [str(arg) for arg in args]

        # Ensure options are stringified or boolean options.
        # Skip None values, which are omitted optional params.

        str_options: StrBoolOptions = {}
        if options:
            str_options = {
                k: stringify_non_bool(v)
                for k, v in options.items()
                if v is not None and v is not False
            }

        return cls(name=name, args=str_args, options=format_options(str_options))

    @property
    def command_str(self) -> str:
        return format_command_str(self.name, self.args, self.parsed_options)

    def __str__(self):
        return f"Command(`{self.command_str}`)"


def as_comment(text: str) -> str:
    return "\n".join(f"# {line}" for line in text.splitlines())


class CommentedCommand(BaseModel):
    """
    A command with an optional comment explaining what it does.
    """

    comment: str | None
    """
    Any additional notes about what this command does and why it may be useful.
    Does not include the # characters.
    """

    command_line: str
    """The full command line string."""

    uses: list[str]
    """Commands used by this command."""

    @field_validator("comment")
    def clean_comment(cls, v: str) -> str | None:
        return single_line(v) if v else None

    @property
    def parsed(self) -> Command:
        return Command.from_command_str(self.command_line)

    @property
    def command_line_with_continuation(self) -> str:
        if "\\\n" in self.command_line:
            raise ValueError("Command line already has line continuations.")
        return self.command_line.replace("\n", "\\\n")

    @property
    def script_str(self) -> str:
        if self.comment:
            return f"{as_comment(self.comment)}\n{self.command_line_with_continuation}"
        else:
            return self.command_line
