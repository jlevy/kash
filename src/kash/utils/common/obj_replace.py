import operator
from collections.abc import Callable
from typing import Any, TypeAlias


class DeleteSentinel:
    pass


DELETE_VALUE = DeleteSentinel()
"""Sentinel value to indicate a list or dict value should be deleted."""


ValueReplacements: TypeAlias = list[tuple[Any, Any]]


def replace_values(
    data: Any, transform: ValueReplacements, eq: Callable[[Any, Any], bool] = operator.eq
) -> Any:
    """
    Recursively replace or remove values from a data structure according to the provided list of
    replacement pairs `(old, new)`. If the new value is `DELETE_VALUE`, the old value is removed
    from list and dictionary values.
    """
    for old_value, new_value in transform:
        if eq(data, old_value):
            if new_value is DELETE_VALUE:
                return None
            else:
                return new_value

    if isinstance(data, dict):
        return {
            k: replace_values(v, transform, eq)
            for k, v in data.items()
            if not any(
                eq(v, old_value) and new_value is DELETE_VALUE for old_value, new_value in transform
            )
        }
    elif isinstance(data, list):
        return [
            replace_values(item, transform, eq)
            for item in data
            if not any(
                eq(item, old_value) and new_value is DELETE_VALUE
                for old_value, new_value in transform
            )
        ]
    else:
        return data


def remove_values(
    data: Any, targets: list[Any], eq: Callable[[Any, Any], bool] = operator.eq
) -> Any:
    return replace_values(data, [(target, DELETE_VALUE) for target in targets], eq)


## Tests


def test_replace_values():
    data = {"a": 1, "b": 2, "c": [3, 4, 5], "d": {"e": 6, "f": 7}}

    transform = [
        (1, None),
        (2, DELETE_VALUE),
        (3, "three"),
        (4, DELETE_VALUE),
        (6, None),
        (7, DELETE_VALUE),
    ]

    expected = {"a": None, "c": ["three", 5], "d": {"e": None}}

    transformed = replace_values(data, transform)

    assert transformed == expected
