from kash.config.logger import get_logger
from kash.exec import kash_action
from kash.exec.preconditions import has_html_body, is_url_item
from kash.model import Format, Item, ItemType
from kash.web_content.file_cache_utils import get_url_html
from kash.web_content.web_extract_readabilipy import extract_text_readabilipy

log = get_logger(__name__)


@kash_action(
    precondition=is_url_item | has_html_body,
    mcp_tool=True,
)
def readability(item: Item) -> Item:
    """
    Extracts clean HTML from a raw HTML item.
    See `markdownify` to also convert to Markdown.
    """
    url, html_content = get_url_html(item)
    page_data = extract_text_readabilipy(url, html_content)

    output_item = item.derived_copy(
        type=ItemType.doc, format=Format.html, body=page_data.clean_html
    )

    return output_item
