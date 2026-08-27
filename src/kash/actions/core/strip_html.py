from __future__ import annotations

from kash.config.logger import get_logger
from kash.exec import kash_action
from kash.exec.preconditions import has_html_body, has_simple_text_body
from kash.model import Format, Item
from kash.utils.common.format_utils import html_to_plaintext
from kash.utils.errors import InvalidInput

log = get_logger(__name__)


@kash_action(
    precondition=has_html_body | has_simple_text_body,
    output_format=Format.markdown,
)
def strip_html(item: Item) -> Item:
    """
    Strip HTML tags from HTML or Markdown. This is a simple filter, simply searching
    for and removing tags by regex. This works well for basic HTML; use `markdownify`
    for complex HTML.
    """
    if not item.body:
        raise InvalidInput("Item must have a body")

    clean_body = html_to_plaintext(item.body)
    output_item = item.derived_copy(format=Format.markdown, body=clean_body)

    return output_item


## Tests


def test_strip_html_declares_markdown_output() -> None:
    action_class = getattr(strip_html, "__action_class__")  # noqa: B009
    action = action_class.create(None)

    assert action.output_format is Format.markdown
