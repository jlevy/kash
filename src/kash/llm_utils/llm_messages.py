from __future__ import annotations

from textwrap import dedent

from pydantic import ValidationInfo

from kash.config.logger import get_logger
from kash.utils.common.string_template import StringTemplate

log = get_logger(__name__)


class Message(str):
    """
    A message for a model or LLM. Just typed convenience wrapper around a string
    that also dedents and strips whitespace for convenience.
    """

    # Pydantic support.
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value: str, _info: ValidationInfo) -> Message:
        return cls(dedent(str(value)).strip())


class MessageTemplate(StringTemplate):
    """
    A template for an LLM request with a single allowed field, "body", useful
    to wrap a string in a prompt.
    """

    def __init__(self, template: str):
        super().__init__(dedent(template).strip(), allowed_fields=["body"])
