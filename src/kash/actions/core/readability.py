from __future__ import annotations

from kash.config.logger import get_logger
from kash.exec import kash_action
from kash.exec.preconditions import has_html_body, is_url_resource
from kash.exec.runtime_settings import current_runtime_settings
from kash.model import Format, Item
from kash.web_content.file_cache_utils import get_url_html
from kash.web_content.web_extract_readabilipy import extract_text_readabilipy

log = get_logger(__name__)


@kash_action(precondition=is_url_resource | has_html_body, output_format=Format.html)
def readability(item: Item) -> Item:
    """
    Extracts clean HTML from a raw HTML item.
    See `markdownify` to also convert to Markdown.
    """

    refetch = current_runtime_settings().refetch
    expiration_sec = 0 if refetch else None
    locator, html_content = get_url_html(item, expiration_sec=expiration_sec)
    page_data = extract_text_readabilipy(locator, html_content)

    output_item = item.derived_copy(format=Format.html, body=page_data.clean_html)

    return output_item
