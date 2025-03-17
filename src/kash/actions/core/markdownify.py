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
def markdownify(item: Item) -> Item:
    """
    Converts a URL or raw HTML item to Markdown, fetching with the content
    cache if needed. Also uses readability to clean up the HTML.
    """
    from markdownify import markdownify as markdownify_convert

    url, html_content = get_url_html(item)
    page_data = extract_text_readabilipy(url, html_content)
    markdown_content = markdownify_convert(page_data.clean_html)

    output_item = item.derived_copy(
        type=ItemType.doc, format=Format.markdown, body=markdown_content
    )
    return output_item
