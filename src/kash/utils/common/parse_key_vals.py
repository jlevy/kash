"""
Tiny parsing library for key-value pairs. Useful for command-line handling of
options like `foo=123` or `bar="some value"`.
"""

from collections.abc import Callable
from enum import Enum
from typing import Any, TypeVar, cast

from kash.utils.common.parse_shell_args import shell_quote, shell_unquote
from kash.utils.common.type_utils import instantiate_as_type


def format_python_str_or_enum(s: Any) -> str:
    if isinstance(s, Enum):
        return s.value
    return repr(s)


T = TypeVar("T")


def parse_key_value(
    key_value_str: str,
    value_parser: Callable[[str], Any] = shell_unquote,
    target_type: type[T] | None = None,
) -> tuple[str, T | None]:
    """
    Parse a key-value string like `foo=123` or `bar="some value"` into a `(key, value)` tuple.
    A string like `foo=` (with only whitespace after the `=`) will yield `("foo", None)`.
    """
    if target_type is None:
        target_type = cast(type[T], str)

    key, _, value_str = key_value_str.partition("=")
    key = key.strip()
    value_str = value_str.strip()

    value: Any | None
    if not value_str:
        value = None
    else:
        value = value_parser(value_str)

    value = instantiate_as_type(value, target_type)

    return key, value


def default_value_formatter(value: Any) -> str:
    if isinstance(value, str):
        return shell_quote(value)
    elif isinstance(value, Enum):
        return value.value
    else:
        return repr(value)


def format_key_value(
    key: str, value: Any, value_formatter: Callable[[Any], str] = default_value_formatter
) -> str:
    """
    Format a key-value pair as a string like `foo=123` or `bar='some value'`.
    """

    def value_str(value: Any) -> str:
        return "" if value is None else value_formatter(value)

    return f"{key}={value_str(value)}"


## Tests


def test_key_value_parsing_and_formatting():
    assert parse_key_value("foo=123") == ("foo", "123")
    assert parse_key_value(" foo='123'") == ("foo", "123")
    assert parse_key_value('bar="some value"') == ("bar", "some value")
    assert parse_key_value("bar = 'some value'") == ("bar", "some value")
    assert parse_key_value("foo=") == ("foo", None)

    assert format_key_value("foo", "123") == "foo=123"
    assert format_key_value("bar", "some value") == "bar='some value'"
    assert format_key_value("foo", None) == "foo="
    assert format_key_value("foo", "") == "foo=''"
