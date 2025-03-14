"""
Tiny parsing library for parsing and writing shell commands, using a simplified
shell syntax that is compatible with Python and xonsh (but not quite the same
as bash!).
"""

import ast
import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import TypeAlias

# Same unsafe chars as shlex.quote(), but also allowing `~`.
_shell_unsafe_re = re.compile(r"[^\w@%+=:,./~-]", re.ASCII)


def is_shell_quoted(arg: str) -> bool:
    """
    Is this a valid, quoted string? Uses Pythonic style quoting.
    """
    if arg.startswith(("'", '"')) and arg.endswith(arg[0]):
        try:
            ast.literal_eval(arg)
            return True
        except (SyntaxError, ValueError):
            return False
    return False


def shell_quote(arg: str, idempotent: bool = False) -> str:
    """
    Quote a string for shell usage, if needed, using simplified shell conventions
    compatible with Python and xonsh. This means simple text words without spaces
    are left unquoted. Prefers single quotes in cases where either could work.
    Uses Pythonic style quoting for more complex strings.
    """
    if idempotent and is_shell_quoted(arg):
        return arg
    has_unsafe = _shell_unsafe_re.search(arg)
    if arg and not has_unsafe:
        return arg
    elif "'" not in arg:
        return f"'{arg}'"
    else:
        return repr(arg)


def shell_unquote(arg: str) -> str:
    """
    Unquote a string using Python conventions, but allow unquoted strings to
    pass through.

    Note this is Pythonic style so *not* as complex as shlex.unquote().
    """
    if arg.startswith(("'", '"')) and arg.endswith(arg[0]):
        try:
            return ast.literal_eval(arg)
        except (SyntaxError, ValueError):
            pass
    return arg


def shell_split(command_str: str) -> list[str]:
    """
    Split a command string into tokens, respecting quotes and backslash escapes.
    """
    tokens = []
    current_token = ""
    in_quote = False
    quote_char = ""
    escape = False
    i = 0
    while i < len(command_str):
        c = command_str[i]
        if escape:
            current_token += c
            escape = False
        elif c == "\\":
            current_token += c
            escape = True
        elif in_quote:
            current_token += c
            if c == quote_char:
                in_quote = False
        elif c in ('"', "'"):
            current_token += c
            in_quote = True
            quote_char = c
        elif c.isspace():
            if current_token:
                tokens.append(current_token)
                current_token = ""
        else:
            current_token += c
        i += 1

    if current_token:
        tokens.append(current_token)

    return tokens


StrBoolOptions: TypeAlias = dict[str, str | bool]
"""
A sorted dict of options, where keys are option names and values are either strings or
boolean flags.
"""


def format_command_str(command: str, args: Iterable[str], options: StrBoolOptions) -> str:
    """
    Format a command string using simplified shell conventions (compatible with Python and xonsh).
    """
    args_str = " ".join(shell_quote(arg, idempotent=True) for arg in args)
    options_str = " ".join(format_options(options))
    return " ".join(filter(bool, [command, args_str, options_str]))


def format_option(key: str, value: str | bool) -> str | None:
    """
    Format a command option string.
    """
    if isinstance(value, str):
        return f"--{key}={shell_quote(value)}"
    elif isinstance(value, bool) and value:
        return f"--{key}"
    elif isinstance(value, bool) and not value:
        return None
    else:
        raise ValueError(f"Unexpected option value type: {repr(value)}")


def format_options(options: StrBoolOptions) -> list[str]:
    """
    Format a list of command options.
    """
    return list(filter(None, (format_option(k, v) for k, v in options.items())))


def parse_option(key_value_str: str) -> tuple[str, str | bool]:
    """
    Parse a key-value string like `--foo=123` or `--bar="some value"` into a `(key, value)`
    tuple.
    """
    # Allow -foo or --foo.
    key_value_str = key_value_str.lstrip("-")
    key, _, value_str = key_value_str.partition("=")
    key = key.strip().replace("-", "_")
    value_str = value_str.strip()
    value = shell_unquote(value_str) if value_str else True

    return key, value


def parse_command_str(command_str: str) -> tuple[str, list[str], StrBoolOptions]:
    """
    Parse a command string into a command name, arguments, and options, using simplified
    shell conventions (compatible with Python and xonsh).

    Commands are expected to be formatted using shell conventions. Arguments and options
    can appear in any order.

    Strings are quoted using Python conventions. (Note this is not standard bash, so we do
    _not_ use shlex.split(). But it is compatible with xonsh.)

    Examples:

    command arg1 arg2 arg 3 --opt1=val1 --opt2=val2 --opt3
    command --opt1="val 1" --opt2 "arg 1" "arg 1" "arg 2"
    """

    tokens = shell_split(command_str)

    name = tokens[0]
    args = []
    options = {}
    for token in tokens[1:]:
        if token.startswith("-"):
            key, value = parse_option(token.lstrip("-"))
            options[key] = value
        else:
            arg = shell_unquote(token)
            args.append(arg)

    return name, args, options


@dataclass(frozen=True)
class ShellArgs:
    """
    Immutable record of parsed command line arguments and options.
    """

    args: list[str]
    options: StrBoolOptions

    @property
    def show_help(self) -> bool:
        return self.options.get("help", False) == True


def parse_shell_args(args_and_opts: list[str]) -> ShellArgs:
    """
    Parse pre-split raw shell input arguments into plain args and options
    (shell arguments starting with `--`).

    All plain args are strings. All options are string values (if they have
    a value) or boolean flags with a True value (indicating they were
    present on the command line with no value provided).

    ["foo", "--opt1", "--opt2='bar baz'"]
      -> ShellArgs(args=["foo"], options={"opt1": True, "opt2": "bar baz"}, show_help=False)

    ["foo", "--help"]
      -> ShellArgs(args=["foo"], options={"help": True})
    """
    args: list[str] = []
    options: StrBoolOptions = {}

    i = 0
    while i < len(args_and_opts):
        if args_and_opts[i].startswith("-"):
            key, value = parse_option(args_and_opts[i])
            options[key] = value
            i += 1
        else:
            args.append(args_and_opts[i])
            i += 1

    return ShellArgs(args=args, options=options)


## Tests


def test_shell_quote_unquote():
    assert is_shell_quoted("'hello world'") == True
    assert is_shell_quoted('"hello\' world"') == True
    assert is_shell_quoted("hello world") == False
    assert is_shell_quoted("'unclosed") == False
    assert is_shell_quoted("'invalid'quote'") == False
    assert is_shell_quoted("already 'quoted'") == False

    assert shell_quote("simple") == "simple"  # No quotes needed
    assert shell_quote("hello world") == "'hello world'"  # Needs quotes due to space
    assert shell_quote("don't") == '"don\'t"'  # Contains single quote
    assert shell_quote("partly 'quoted'") == "\"partly 'quoted'\""  # Needs proper quoting
    assert shell_quote("'hello'", idempotent=True) == "'hello'"  # Already properly quoted
    assert shell_unquote(shell_quote("'hello'", idempotent=False)) == "'hello'"

    assert shell_unquote("'hello world'") == "hello world"
    assert shell_unquote('"hello world"') == "hello world"
    assert shell_unquote("unquoted") == "unquoted"  # Passes through
    assert shell_unquote("'invalid'quote'") == "'invalid'quote'"  # Invalid quotes pass through


def test_shell_split():
    assert shell_split("simple command") == ["simple", "command"]
    assert shell_split('quoted "string with spaces"') == ["quoted", '"string with spaces"']
    assert shell_split("""mixed 'single' and "double" quotes""") == [
        "mixed",
        "'single'",
        "and",
        '"double"',
        "quotes",
    ]
    assert shell_split(r"escaped \"quotes\" and spaces") == [
        r"escaped",
        r"\"quotes\"",
        "and",
        "spaces",
    ]
    assert shell_split("nested \"quotes 'inside' quotes\"") == [
        "nested",
        "\"quotes 'inside' quotes\"",
    ]
    assert shell_split('command with "quoted argument" and unquoted') == [
        "command",
        "with",
        '"quoted argument"',
        "and",
        "unquoted",
    ]
    assert shell_split("") == []
    assert shell_split(" \n  ") == []


def test_parse_and_format_command_str():
    # Test basic parsing and formatting.
    command_str = "mycommand arg1 arg2 --option1=value1 --flag"
    name, args, options = parse_command_str(command_str)
    assert name == "mycommand"
    assert args == ["arg1", "arg2"]
    assert options == {"option1": "value1", "flag": True}

    # Test roundtrip.
    reconstructed = format_command_str(name, args, options)
    assert reconstructed == command_str

    # Test with quoted arguments and option values.
    complex_command = "complex 'quoted arg' --option='quoted value' --flag 'spaced arg'"
    name, args, options = parse_command_str(complex_command)
    assert name == "complex"
    assert args == ["quoted arg", "spaced arg"]
    assert options == {"option": "quoted value", "flag": True}

    # Test roundtrip with complex command.
    reconstructed = format_command_str(name, args, options)
    assert reconstructed == "complex 'quoted arg' 'spaced arg' --option='quoted value' --flag"

    # Test with empty arguments and options.
    empty_command = "empty_cmd"
    name, args, options = parse_command_str(empty_command)
    assert name == "empty_cmd"
    assert args == []
    assert options == {}

    # Test roundtrip with empty command.
    reconstructed = format_command_str(name, args, options)
    assert reconstructed == empty_command


def test_parse_shell_args():
    args = [
        "pos1",
        "pos2",
        "--key1=value1",
        "--key2",
        "pos3",
        "-k3=value3",
        "--key4='two words'",
        "--help",
    ]
    shell_args = parse_shell_args(args)

    assert shell_args.args == [
        "pos1",
        "pos2",
        "pos3",
    ]
    assert shell_args.options == {
        "key1": "value1",
        "key2": True,
        "k3": "value3",
        "key4": "two words",
        "help": True,
    }
    assert shell_args.show_help == True
