from __future__ import annotations

from kash.config.logger import get_logger
from kash.exec import kash_action
from kash.model import ONE_OR_MORE_ARGS, ActionInput, ActionResult, Param
from kash.utils.errors import InvalidInput

log = get_logger(__name__)


@kash_action(
    expected_args=ONE_OR_MORE_ARGS,
    params=(
        Param(
            "separator",
            "String to use between concatenated items.",
            type=str,
            default_value="\n\n",
        ),
    ),
)
def concat_docs(input: ActionInput, separator: str = "\n\n") -> ActionResult:
    """
    Concatenate multiple text items into a single document with the specified
    separator between each piece.
    """
    items = input.items

    if not items:
        raise InvalidInput("No items provided for concatenation")

    # Collect all bodies
    bodies = []
    for item in items:
        if not item.body:
            raise InvalidInput(f"Item has no body: {item.store_path}")
        bodies.append(item.body)

    # Concatenate with the specified separator
    concat_body = separator.join(bodies)

    # Create title
    count = len(items)
    title = f"Concat ({count} doc{'s' if count != 1 else ''})"

    # Create result item based on first item
    result_item = items[0].derived_copy(body=concat_body, title=title, original_filename=None)

    return ActionResult([result_item])
