from dataclasses import dataclass

from kash.config.logger import get_logger
from kash.exec.preconditions import is_url_resource
from kash.model.items_model import Format, Item, ItemType
from kash.model.paths_model import StorePath
from kash.utils.common.format_utils import fmt_loc
from kash.utils.common.url import Url, is_url
from kash.utils.common.url_slice import add_slice_to_url, parse_url_slice
from kash.utils.errors import InvalidInput
from kash.web_content.web_page_model import WebPageData

log = get_logger(__name__)


@dataclass(frozen=True)
class FetchItemResult:
    """
    Result of fetching a URL item.
    """

    item: Item

    was_cached: bool
    """Whether this item was already present in cache (or if we skipped the fetch
    because we already had the data)."""

    page_data: WebPageData | None = None
    """If the item was fetched from a URL via the web content cache,
    this will hold additional metadata whether it was cached."""


def fetch_url_item(
    locator: Url | StorePath,
    *,
    save_content: bool = True,
    refetch: bool = False,
    cache: bool = True,
    overwrite: bool = True,
) -> FetchItemResult:
    """
    Fetch or load an URL or path. For a URL, will fetch the content and metadata and save
    as an item in the workspace.

    Returns:
        The fetched or loaded item, already saved to the workspace.
    """
    from kash.workspaces import current_ws

    ws = current_ws()
    if is_url(locator):
        # Import or find URL as a resource in the current workspace.
        store_path = ws.import_item(locator, as_type=ItemType.resource)
        item = ws.load(store_path)
    elif isinstance(locator, StorePath):
        item = ws.load(locator)
        if not is_url_resource(item):
            raise InvalidInput(f"Not a URL resource: {fmt_loc(locator)}")
    else:
        raise InvalidInput(f"Not a URL or URL resource: {fmt_loc(locator)}")

    return fetch_url_item_content(
        item,
        save_content=save_content,
        refetch=refetch,
        cache=cache,
        overwrite=overwrite,
    )


def fetch_url_item_content(
    item: Item,
    *,
    save_content: bool = True,
    refetch: bool = False,
    cache: bool = True,
    overwrite: bool = True,
) -> FetchItemResult:
    """
    Fetch content and metadata for a URL using a media service if we
    recognize the URL as a known media service. Otherwise, fetch and extract the
    metadata and content from the web page and save it to the URL item.

    If `save_content` is true, a copy of the content is also saved to the workspace
    as a resource item.

    If `cache` is true, the content is also cached in the local file cache.

    If `overwrite` is true, the item is saved at the same location every time.
    This is useful to keep resource filenames consistent.

    Returns:
        The fetched or loaded item, already saved to the workspace.
    """
    from kash.media_base.media_services import get_media_metadata
    from kash.web_content.canon_url import canonicalize_url
    from kash.web_content.web_extract import fetch_page_content
    from kash.workspaces import current_ws

    ws = current_ws()
    if not refetch and item.title and item.description and item.body:
        log.info(
            "Already have title, description, and body, will not fetch: %s",
            item.fmt_loc(),
        )
        return FetchItemResult(item, was_cached=True)

    if not item.url:
        raise InvalidInput(f"No URL for item: {item.fmt_loc()}")

    url = canonicalize_url(item.url)
    log.info("No metadata for URL, will fetch: %s", url)

    # Prefer fetching metadata from media using the media service if possible.
    # Data is cleaner and YouTube for example often blocks regular scraping.
    media_metadata = get_media_metadata(url)
    url_item: Item | None = None
    content_item: Item | None = None
    page_data: WebPageData | None = None

    if media_metadata:
        url_item = Item.from_media_metadata(media_metadata)
        # Preserve and canonicalize any slice suffix on the URL.
        _base_url, slice = parse_url_slice(item.url)
        if slice:
            new_url = add_slice_to_url(media_metadata.url, slice)
            if new_url != item.url:
                log.info("Updated URL from metadata and added slice: %s", new_url)
            url_item.url = new_url

        url_item = item.merged_copy(url_item)
    else:
        page_data = fetch_page_content(url, refetch=refetch, cache=cache)
        url_item = Item(
            type=ItemType.resource,
            format=Format.url,
            url=url,
            title=page_data.title or item.title,
            description=page_data.description or item.description,
            thumbnail_url=page_data.thumbnail_url or item.thumbnail_url,
        )
        if save_content:
            assert page_data.saved_content
            assert page_data.format_info
            content_item = url_item.new_copy_with(
                external_path=str(page_data.saved_content),
                # Use the original filename, not the local cache filename (which has a hash suffix).
                original_filename=item.get_filename(),
                format=page_data.format_info.format,
            )

    if not url_item.title:
        log.warning("Failed to fetch page data: title is missing: %s", item.url)

    # Now save the updated URL item and also the content item if we have one.
    ws.save(url_item, overwrite=overwrite)
    assert url_item.store_path
    if content_item:
        ws.save(content_item, overwrite=overwrite)
        assert content_item.store_path
        log.info(
            "Saved both URL and content item: %s, %s",
            url_item.fmt_loc(),
            content_item.fmt_loc(),
        )
    else:
        log.info("Saved URL item (no content): %s", url_item.fmt_loc())

    was_cached = bool(
        not page_data or (page_data.cache_result and page_data.cache_result.was_cached)
    )
    return FetchItemResult(
        item=content_item or url_item, was_cached=was_cached, page_data=page_data
    )
