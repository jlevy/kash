from chopdiff.html.html_in_md import div_wrapper

from kash.config.logger import get_logger
from kash.exec import kash_action
from kash.model import ONE_OR_MORE_ARGS, ActionInput, ActionResult, Param
from kash.utils.errors import InvalidInput

log = get_logger(__name__)


@kash_action(
    expected_args=ONE_OR_MORE_ARGS,
    params=(
        Param(
            "class_name",
            "CSS class name to use for wrapping each document in a div.",
            type=str,
            default_value="doc",
        ),
    ),
)
def combine_docs(input: ActionInput, class_name: str = "page") -> ActionResult:
    """
    Combine multiple text items into a single document, wrapping each piece
    in a div with the specified CSS class.
    """
    items = input.items

    if not items:
        raise InvalidInput("No items provided for combination")

    # Create wrapper function
    wrapper = div_wrapper(class_name=class_name)

    # Collect and wrap all bodies
    wrapped_bodies = []
    for item in items:
        if not item.body:
            raise InvalidInput(f"Item has no body: {item.store_path}")
        wrapped_bodies.append(wrapper(item.body))

    # Concatenate with double newlines
    combined_body = "\n\n".join(wrapped_bodies)

    # Create title
    count = len(items)
    title = f"Combined ({count} doc{'s' if count != 1 else ''})"

    # Create result item based on first item
    result_item = items[0].derived_copy(body=combined_body, title=title, original_filename=None)

    return ActionResult([result_item])
