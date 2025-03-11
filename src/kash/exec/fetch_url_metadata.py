from kash.config.logger import get_logger
from kash.errors import InvalidInput
from kash.exec.precondition_defs import is_url_item
from kash.media_base.media_services import get_media_metadata
from kash.model.items_model import Item, ItemType
from kash.model.paths_model import StorePath
from kash.util.format_utils import fmt_loc
from kash.util.url import is_url, Url
from kash.web_content.canon_url import canonicalize_url
from kash.web_content.web_extract import fetch_extract
from kash.workspaces import current_workspace

log = get_logger(__name__)


def fetch_url_metadata(
    locator: Url | StorePath, use_cache: bool = True, refetch: bool = False
) -> Item:
    ws = current_workspace()
    if is_url(locator):
        # Import or find URL as a resource in the current workspace.
        store_path = ws.import_item(locator, as_type=ItemType.resource)
        item = ws.load(store_path)
    elif isinstance(locator, StorePath):
        item = ws.load(locator)
        if not is_url_item(item):
            raise InvalidInput(f"Not a URL resource: {fmt_loc(locator)}")
    else:
        raise InvalidInput(f"Not a URL or URL resource: {fmt_loc(locator)}")

    return fetch_url_item_metadata(item, use_cache=use_cache, refetch=refetch)


def fetch_url_item_metadata(item: Item, use_cache: bool = True, refetch: bool = False) -> Item:
    """
    Fetch metadata for a URL using a media service if we recognize the URL,
    and otherwise fetching and extracting it from the web page HTML.
    """
    ws = current_workspace()
    if not refetch and item.title and item.description:
        log.message(
            "Already have title and description, will not fetch metadata: %s", item.fmt_loc()
        )
        return item

    if not item.url or not item.is_url_resource():
        raise InvalidInput(f"No URL for item: {item.fmt_loc()}")

    url = canonicalize_url(item.url)
    log.message("No metadata for URL, will fetch: %s", url)

    # Prefer fetching metadata from media using the media service if possible.
    # Data is cleaner and YouTube for example often blocks regular scraping.
    media_metadata = get_media_metadata(url)
    if media_metadata:
        fetched_item = Item.from_media_metadata(media_metadata)
        fetched_item = item.merged_copy(fetched_item)
    else:

        page_data = fetch_extract(url, use_cache=use_cache)
        fetched_item = item.new_copy_with(
            title=page_data.title or item.title,
            description=page_data.description or item.description,
            thumbnail_url=page_data.thumbnail_url or item.thumbnail_url,
        )

    if not fetched_item.title:
        log.warning("Failed to fetch page data: title is missing: %s", item.url)

    ws.save(fetched_item)

    return fetched_item
