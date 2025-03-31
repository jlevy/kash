from pathlib import Path

from kash.config.logger import get_logger
from kash.file_storage.file_store import FileStore
from kash.model.items_model import Item, ItemType
from kash.model.paths_model import StorePath
from kash.utils.common.url import Locator, Url, is_url
from kash.utils.errors import InvalidInput
from kash.utils.file_utils.file_formats_model import Format
from kash.web_content.canon_url import canonicalize_url

# TODO: Clean this up, move into FileStore.

log = get_logger(__name__)


def import_url(ws: FileStore, url: Url) -> Item:
    """
    Import a URL as a resource. Does not fetch metadata.
    """
    canon_url = canonicalize_url(url)
    log.message(
        "Importing URL: %s%s", canon_url, f" canonicalized from {url}" if url != canon_url else ""
    )
    item = Item(ItemType.resource, url=canon_url, format=Format.url)
    # No need to overwrite any resource we already have for the identical URL.
    store_path = ws.save(item, overwrite=False)
    # Load to fill in any metadata we may already have.
    item = ws.load(store_path)
    return item


def import_and_load(ws: FileStore, locator: Locator | str) -> Item:
    """
    Ensure that a URL or file path is imported into the workspace and
    return the Item.
    """

    if isinstance(locator, str) and is_url(locator):
        log.message("Importing locator as URL: %r", locator)
        item = import_url(ws, Url(locator))
    else:
        if isinstance(locator, StorePath):
            log.info("Locator is in the file store: %r", locator)
            # It's already a StorePath.
            item = ws.load(locator)
        else:
            log.message("Importing locator as local path: %r", locator)
            path = Path(locator)
            if not path.exists():
                raise InvalidInput(f"File not found: {path}")

            store_path = ws.import_item(path)
            item = ws.load(store_path)

    return item
