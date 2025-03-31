from __future__ import annotations

from collections.abc import Callable
from typing import ClassVar

from prettyfmt import fmt_words
from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema

from kash.model.items_model import Item
from kash.utils.errors import PreconditionFailure


class Precondition:
    """
    A Precondition is a criterion that can be used to filter `Items` or qualify which
    `Items` may be inputs to given `Actions`. Function can return a bool or raise
    `PreconditionFailure`.

    Preconditions can be combined with `&`, `|`, and `~` operators.
    """

    def __init__(self, func: Callable[[Item], bool], name: str | None = None):
        self.func = func
        self.name: str = name or func.__name__

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler: GetCoreSchemaHandler):
        return core_schema.is_instance_schema(cls)

    def check(self, item: Item, info: str | None = None) -> None:
        if not self(item):
            raise PreconditionFailure(
                fmt_words(
                    "Precondition",
                    f"for {info}" if info else "",
                    f"not satisfied: {self} is false for {item.fmt_loc()}",
                )
            )

    def __call__(self, item: Item) -> bool:
        try:
            return self.func(item)
        except PreconditionFailure:
            return False

    def __and__(self, other: Precondition) -> Precondition:
        return Precondition(lambda item: self(item) and other(item), f"{self.name} & {other.name}")

    def __or__(self, other: Precondition) -> Precondition:
        return Precondition(lambda item: self(item) or other(item), f"{self.name} | {other.name}")

    def __invert__(self) -> Precondition:
        return Precondition(lambda item: not self(item), f"~{self.name}")

    def __str__(self) -> str:
        return f"`{self.name}`"

    @staticmethod
    def and_all(*preconditions: Precondition) -> Precondition:
        if not preconditions:
            return Precondition(lambda item: True, "always")
        combined = preconditions[0]
        for precondition in preconditions[1:]:
            combined = combined & precondition
        return combined

    @staticmethod
    def or_all(*preconditions: Precondition) -> Precondition:
        if not preconditions:
            return Precondition(lambda item: False, "never")
        combined = preconditions[0]
        for precondition in preconditions[1:]:
            combined = combined | precondition
        return combined

    always: ClassVar[Precondition]
    """
    Precondition that is always true.
    """

    never: ClassVar[Precondition]
    """
    Precondition that is always false.
    """


Precondition.always = Precondition(lambda item: True, "always")

Precondition.never = Precondition(lambda item: False, "never")
