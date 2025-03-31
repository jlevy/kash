from __future__ import annotations

from textwrap import dedent
from typing import Any

from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema
from pydantic_core.core_schema import (
    no_info_after_validator_function,
    str_schema,
    to_string_ser_schema,
)

from kash.utils.common.string_template import StringTemplate


class Message(str):
    """
    A message for a model or LLM. Just typed convenience wrapper around a string
    that also dedents and strips whitespace for convenience.
    """

    @classmethod
    def _validate(cls, value: Any) -> Message:
        return cls(dedent(str(value)).strip())

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return no_info_after_validator_function(
            cls._validate, str_schema(), serialization=to_string_ser_schema()
        )


class MessageTemplate(StringTemplate):
    """
    A template for an LLM request with a single allowed field, "body", useful
    to wrap a string in a prompt.
    """

    def __init__(self, template: str):
        super().__init__(dedent(template).strip(), allowed_fields=["body"])
