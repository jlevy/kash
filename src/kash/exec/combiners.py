from collections.abc import Callable
from typing import TypeAlias

from chopdiff.divs import GROUP, ORIGINAL, div, div_insert_wrapped
from chopdiff.divs.parse_divs import parse_divs_single
from chopdiff.html import div_wrapper
from chopdiff.html.html_in_md import Wrapper

from kash.config.logger import get_logger
from kash.model.actions_model import ActionResult
from kash.model.items_model import Item, ItemRelations, ItemType
from kash.model.operations_model import OperationSummary
from kash.model.paths_model import StorePath
from kash.utils.common.type_utils import not_none
from kash.utils.errors import InvalidInput

log = get_logger(__name__)

Combiner: TypeAlias = Callable[[list[Item], list[ActionResult]], Item]


def combine_items(
    inputs: list[Item],
    results: list[ActionResult],
    body_combiner: Callable[[list[str]], str],
) -> Item:
    """
    Combine the results from multiple actions on the same inputs into a single item,
    using the provided callable to combine the bodies.
    """

    if len(inputs) < 1:
        raise InvalidInput("Expected at least one input to combine: %s", inputs)

    # Assemble the parts.
    parts: list[Item] = []
    for result in results:
        for part in result.items:
            if not part.body:
                raise InvalidInput("Item result must have a body: %s", part)
            if not part.store_path:
                raise InvalidInput("Item result must have a store path: %s", part)

            parts.append(part)

    # Combine the body using the provided body combiner.
    combo_body = body_combiner([not_none(part.body) for part in parts])

    combo_title = f"{inputs[0].title}"
    if len(inputs) > 1:
        combo_title += f" and {len(inputs) - 1} others"

    relations = ItemRelations(derived_from=[StorePath(not_none(part.store_path)) for part in parts])
    combo_result = Item(
        title=combo_title,
        body=combo_body,
        type=ItemType.doc,
        format=results[0].items[0].format,
        relations=relations,
    )

    # History when combining results is a little complicated, so let's just concatenate
    # all the history lists but avoid duplicates.
    result_items = [item for result in results for item in result.items]
    unique_ops: set[OperationSummary] = set()
    combo_result.history = []

    for item in result_items:
        for entry in item.history or []:
            if entry not in unique_ops:
                unique_ops.add(entry)
                combo_result.history.append(entry)

    return combo_result


def combine_with_wrappers(
    bodies: list[str],
    wrappers: list[Wrapper] | None = None,
    separator: str = "\n\n",
) -> str:
    if wrappers:
        bodies = [wrappers[i](body) for i, body in enumerate(bodies)]
    return separator.join(bodies)


def combine_as_paragraphs(inputs: list[Item], results: list[ActionResult]) -> Item:
    """
    Combine the outputs of multiple actions into a single item, separating each part with
    paragraph breaks.
    """
    return combine_items(inputs, results, combine_with_wrappers)


def combine_with_divs(*class_names: str) -> Combiner:
    """
    Combine the outputs of multiple actions into a single item, wrapping each part in a div with
    the corresponding name.
    """

    def combiner(inputs: list[Item], results: list[ActionResult]) -> Item:
        wrappers = [div_wrapper(class_name, padding="\n\n") for class_name in class_names]
        return combine_items(
            inputs, results, lambda bodies: combine_with_wrappers(bodies, wrappers)
        )

    return combiner


def combine_as_div_group(child_class: str) -> Combiner:
    """
    Combine the outputs of multiple actions into a single group div, inserting new parts
    as sibling elements, with the first as the original.
    """

    def combiner(inputs: list[Item], results: list[ActionResult]) -> Item:
        def body_combiner(bodies: list[str]) -> str:
            element = parse_divs_single(bodies[0])
            new_children = [div(child_class, content) for content in bodies[1:]]

            return div_insert_wrapped(
                element, new_children, container_class=GROUP, original_class=ORIGINAL
            )

        return combine_items(inputs, results, body_combiner)

    return combiner
