from kash.config.logger import get_logger
from kash.exec import kash_action
from kash.exec.preconditions import has_html_body, has_text_body
from kash.model import Format, Item, ItemType
from kash.utils.common.format_utils import html_to_plaintext
from kash.utils.errors import InvalidInput

log = get_logger(__name__)


@kash_action(precondition=has_html_body | has_text_body)
def strip_html(item: Item) -> Item:
    """
    Strip HTML tags from HTML or Markdown. This is a simple filter, simply searching
    for and removing tags by regex. This works well for basic HTML; use `markdownify`
    for complex HTML.
    """
    if not item.body:
        raise InvalidInput("Item must have a body")

    clean_body = html_to_plaintext(item.body)
    output_item = item.derived_copy(
        type=ItemType.doc,
        format=Format.markdown,
        body=clean_body,
    )

    return output_item
