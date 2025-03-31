import re
from pathlib import Path

from kash.config.logger import get_logger
from kash.exec import kash_action
from kash.exec.preconditions import is_markdown
from kash.model import ONE_OR_MORE_ARGS, ActionInput, ActionResult, ItemType, Param
from kash.utils.common.type_utils import not_none
from kash.utils.errors import InvalidInput

log = get_logger(__name__)


@kash_action(
    expected_args=ONE_OR_MORE_ARGS,
    precondition=is_markdown,
    params=(
        Param(
            "md_template",
            "Path for the markdown template to use for formatting. This is plain Markdown "
            "with curly-brace {name} variables for values to insert.",
            type=Path,
            default_value=Path("template.md"),
        ),
    ),
)
def format_markdown_template(
    input: ActionInput, md_template: Path = Path("template.md")
) -> ActionResult:
    """
    Format the given text documents into a single document using the given
    template. This is a simple way to generate combined docs from individual
    pieces or sections, e.g. assembling a readme from a few docs.

    As a convenience, the variables in the template need only be unique
    matching prefixes of the filename of each item, e.g. {body} for a file
    named `body.md` or `body_new_01.md`.
    """
    template_path = md_template if md_template else Path("template.md")
    items = input.items

    with open(template_path) as f:
        template = f.read()

    # Identify variables in the template.
    variables: list[str] = re.findall(r"\{(\w+)\}", template)

    if len(variables) != len(items):
        raise InvalidInput(
            f"Number of inputs ({len(items)} items) does not match the"
            f" number of variables ({len(variables)}) in the template"
        )

    # Create a dictionary to map variable names to item bodies.
    item_map: dict[str, str] = {}
    unmatched_items = set(range(len(items)))

    for var in variables:
        matches = []
        for i, item in enumerate(items):
            store_path = not_none(item.store_path)
            filename = Path(store_path).stem

            if not item.body:
                raise InvalidInput(f"Item has no body: {store_path}")

            if filename.startswith(var):
                matches.append((i, item))

        if len(matches) == 0:
            raise InvalidInput(f"No matching item found for variable: `{var}`")
        elif len(matches) > 1:
            raise InvalidInput(
                f"Multiple items match variable `{var}`: {[items[i].store_path for i, _ in matches]}"
            )

        index, matched_item = matches[0]
        item_map[var] = matched_item.body
        unmatched_items.remove(index)

    if unmatched_items:
        raise InvalidInput(f"Unmatched items: {[items[i].store_path for i in unmatched_items]}")

    # Format the body using the mapped items.
    body = template.format(**item_map)

    result_item = items[0].derived_copy(
        type=ItemType.doc,
        body=body,
    )

    return ActionResult([result_item])
