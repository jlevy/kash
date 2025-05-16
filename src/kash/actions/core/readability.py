from kash.config.logger import get_logger
from kash.exec import kash_action
from kash.exec.preconditions import has_html_body, is_url_resource
from kash.model import Format, Item
from kash.model.params_model import common_params
from kash.web_content.file_cache_utils import get_url_html
from kash.web_content.web_extract_readabilipy import extract_text_readabilipy

log = get_logger(__name__)


@kash_action(
    precondition=is_url_resource | has_html_body,
    params=common_params("refetch"),
    mcp_tool=True,
)
def readability(item: Item, refetch: bool = False) -> Item:
    """
    Extracts clean HTML from a raw HTML item.
    See `markdownify` to also convert to Markdown.
    """
    expiration_sec = 0 if refetch else None
    url, html_content = get_url_html(item, expiration_sec=expiration_sec)
    page_data = extract_text_readabilipy(url, html_content)

    output_item = item.derived_copy(format=Format.html, body=page_data.clean_html)

    return output_item
