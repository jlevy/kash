from __future__ import annotations

import threading
from collections.abc import Callable

from prettyfmt import fmt_lines, fmt_path

from kash.config.logger import get_logger
from kash.file_storage.store_filenames import join_suffix, parse_item_filename
from kash.model.items_model import Item, ItemId
from kash.model.paths_model import StorePath
from kash.utils.common.uniquifier import Uniquifier
from kash.utils.errors import InvalidFilename, SkippableError

log = get_logger(__name__)


class ItemIdIndex:
    """
    Index of item identities and historical filenames within a workspace.

    - Tracks a mapping of `ItemId -> StorePath` for quick lookups
    - Tracks historical slugs via `Uniquifier` to generate unique names consistently

    TODO: Should add a file system watcher to make this always consistent with disk state.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.uniquifier = Uniquifier()
        self.id_map: dict[ItemId, StorePath] = {}

    def reset(self) -> None:
        """
        Clear all index state.
        """
        with self._lock:
            log.info("ItemIdIndex: reset")
            self.uniquifier = Uniquifier()
            self.id_map.clear()

    def __len__(self) -> int:
        """
        Number of unique names tracked.
        """
        with self._lock:
            return len(self.uniquifier)

    def uniquify_slug(self, slug: str, full_suffix: str) -> tuple[str, list[str]]:
        """
        Return a unique slug and historic slugs for the given suffix.
        """
        with self._lock:
            # This updates internal history as a side-effect. Log for consistency.
            log.info("ItemIdIndex: uniquify slug '%s' with suffix '%s'", slug, full_suffix)
            return self.uniquifier.uniquify_historic(slug, full_suffix)

    def index_item(
        self, store_path: StorePath, load_item: Callable[[StorePath], Item]
    ) -> StorePath | None:
        """
        Update the index with an item at `store_path`.
        Returns store path of any duplicate item with the same id, otherwise None.
        """
        name, item_type, _format, file_ext = parse_item_filename(store_path)
        if not file_ext:
            log.debug(
                "Skipping file with unrecognized name or extension: %s",
                fmt_path(store_path),
            )
            return None

        with self._lock:
            full_suffix = join_suffix(item_type.name, file_ext.name) if item_type else file_ext.name
            # Track unique name history
            self.uniquifier.add(name, full_suffix)

        log.info("ItemIdIndex: indexing %s", fmt_path(store_path))

        # Load item outside the lock to avoid holding it during potentially slow I/O
        try:
            item = load_item(store_path)
        except (ValueError, SkippableError) as e:
            log.warning(
                "ItemIdIndex: could not index file, skipping: %s: %s",
                fmt_path(store_path),
                e,
            )
            return None

        dup_path: StorePath | None = None
        with self._lock:
            item_id = item.item_id()
            if item_id:
                old_path = self.id_map.get(item_id)
                if old_path and old_path != store_path:
                    dup_path = old_path
                    log.info(
                        "ItemIdIndex: duplicate id detected %s:\n%s",
                        item_id,
                        fmt_lines([old_path, store_path]),
                    )
                self.id_map[item_id] = store_path
                log.info("ItemIdIndex: set id %s -> %s", item_id, fmt_path(store_path))

        return dup_path

    def unindex_item(self, store_path: StorePath, load_item: Callable[[StorePath], Item]) -> None:
        """
        Remove an item from the id index.
        """
        try:
            # Load item outside the lock to avoid holding it during potentially slow I/O
            item = load_item(store_path)
            item_id = item.item_id()
            if item_id:
                with self._lock:
                    try:
                        self.id_map.pop(item_id, None)
                        log.info("ItemIdIndex: removed id %s for %s", item_id, fmt_path(store_path))
                    except KeyError:
                        pass
        except (FileNotFoundError, InvalidFilename):
            pass

    def find_store_path_by_id(self, item_id: ItemId) -> StorePath | None:
        with self._lock:
            return self.id_map.get(item_id)
