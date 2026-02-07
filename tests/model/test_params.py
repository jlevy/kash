"""Tests for Param validation, json_schema generation, and properties."""

from __future__ import annotations

from enum import Enum

from kash.model.params_model import Param
from kash.utils.errors import InvalidInput


class Color(Enum):
    red = "red"
    green = "green"
    blue = "blue"


def test_validate_value_enum():
    param = Param(name="color", description="Pick a color", type=Color)
    param.validate_value(Color.red)  # valid member should not raise


def test_validate_value_closed_str():
    param = Param(
        name="size", description="Size", type=str,
        valid_str_values=["small", "medium", "large"],
    )
    param.validate_value("small")  # should not raise

    try:
        param.validate_value("huge")
        raise AssertionError("Expected InvalidInput")
    except InvalidInput:
        pass


def test_validate_value_open_ended_str():
    param = Param(
        name="query", description="Query", type=str,
        valid_str_values=["example1", "example2"],
        is_open_ended=True,
    )
    # Open-ended params accept any value even if not in the suggested list.
    param.validate_value("anything_goes")


def test_json_schema_bool():
    param = Param(name="verbose", description="Verbose output", type=bool, default_value=False)
    schema = param.json_schema()
    assert schema["type"] == "boolean"
    assert schema["default"] is False


def test_json_schema_int():
    param = Param(name="count", description="Item count", type=int, default_value=10)
    schema = param.json_schema()
    assert schema["type"] == "integer"
    assert schema["default"] == 10


def test_json_schema_enum():
    param = Param(name="color", description="Color choice", type=Color, default_value=Color.red)
    schema = param.json_schema()
    assert schema["type"] == "string"
    assert schema["enum"] == ["red", "green", "blue"]
    assert schema["default"] == "red"


def test_json_schema_closed_str():
    param = Param(
        name="level", description="Log level", type=str,
        valid_str_values=["debug", "info", "warn"],
    )
    schema = param.json_schema()
    assert schema["type"] == "string"
    assert schema["enum"] == ["debug", "info", "warn"]


def test_properties():
    bool_param = Param(name="flag", description="A flag", type=bool)
    assert bool_param.is_bool
    assert not bool_param.is_path
    assert bool_param.shell_prefix == "--flag"
    assert bool_param.display == "--flag"

    str_param = Param(name="output", description="Output file", type=str)
    assert not str_param.is_bool
    assert str_param.shell_prefix == "--output="
    assert str_param.display == "--output=VALUE"


def test_valid_values_from_enum():
    param = Param(name="color", description="Color", type=Color)
    assert param.valid_values == ["red", "green", "blue"]


def test_with_default():
    param = Param(name="count", description="Count", type=int)
    assert param.default_value is None
    updated = param.with_default(42)
    assert updated.default_value == 42
    assert param.default_value is None  # original unchanged


def test_invalid_param_name():
    try:
        Param(name="", description="empty", type=str)
        raise AssertionError("Expected ValueError")
    except ValueError:
        pass

    try:
        Param(name="bad-name", description="hyphen", type=str)
        raise AssertionError("Expected ValueError")
    except ValueError:
        pass


def test_default_type_mismatch():
    try:
        Param(name="count", description="Count", type=int, default_value="not_an_int")
        raise AssertionError("Expected TypeError")
    except TypeError:
        pass
