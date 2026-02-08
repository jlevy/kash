"""Tests for item_id_index: ItemIdIndex lookup and duplicate detection."""

from __future__ import annotations

from unittest.mock import MagicMock

from kash.file_storage.item_id_index import ItemIdIndex
from kash.model.items_model import IdType, Item, ItemId, ItemType
from kash.utils.common.url import Url
from kash.model.paths_model import StorePath
from kash.utils.errors import SkippableError
from kash.utils.file_utils.file_formats_model import Format


def _url_resource(url: str) -> Item:
    """Create a URL resource item that produces a valid ItemId."""
    return Item(
        title="Resource",
        type=ItemType.resource,
        format=Format.url,
        url=Url(url),
    )


class TestItemIdIndex:
    def test_starts_empty(self):
        idx = ItemIdIndex()
        assert len(idx) == 0

    def test_reset_clears_state(self):
        idx = ItemIdIndex()
        item_id = ItemId(ItemType.resource, IdType.url, "https://example.com")
        idx.id_map[item_id] = StorePath("test.resource.url")
        idx.reset()
        assert len(idx.id_map) == 0

    def test_index_item_and_find(self):
        """index_item stores the id mapping; find_store_path_by_id retrieves it."""
        idx = ItemIdIndex()
        item = _url_resource("https://example.com/page")
        item_id = item.item_id()
        assert item_id is not None

        loader = MagicMock(return_value=item)
        idx.index_item(StorePath("test.resource.yml"), loader)
        found = idx.find_store_path_by_id(item_id)
        assert found == StorePath("test.resource.yml")

    def test_duplicate_detection(self):
        """index_item returns the old path when a duplicate id is found."""
        idx = ItemIdIndex()
        item = _url_resource("https://example.com/dup")
        loader = MagicMock(return_value=item)

        dup1 = idx.index_item(StorePath("first.resource.yml"), loader)
        assert dup1 is None  # No previous entry

        dup2 = idx.index_item(StorePath("second.resource.yml"), loader)
        assert dup2 == StorePath("first.resource.yml")  # Detected duplicate

    def test_unindex_item_removes(self):
        """unindex_item removes an item from the id map."""
        idx = ItemIdIndex()
        item = _url_resource("https://example.com/remove")
        item_id = item.item_id()
        assert item_id is not None
        loader = MagicMock(return_value=item)

        idx.index_item(StorePath("test.resource.yml"), loader)
        assert idx.find_store_path_by_id(item_id) is not None

        idx.unindex_item(StorePath("test.resource.yml"), loader)
        assert idx.find_store_path_by_id(item_id) is None

    def test_load_error_skipped(self):
        """Items that fail to load are silently skipped."""
        idx = ItemIdIndex()

        def bad_loader(_sp):
            raise SkippableError("broken")

        result = idx.index_item(StorePath("bad.doc.md"), bad_loader)
        assert result is None

    def test_find_nonexistent_returns_none(self):
        idx = ItemIdIndex()
        item_id = ItemId(ItemType.resource, IdType.url, "https://nonexistent.com")
        assert idx.find_store_path_by_id(item_id) is None
