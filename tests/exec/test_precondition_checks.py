"""Tests for precondition_checks: action matching and item filtering."""

from __future__ import annotations

from unittest.mock import MagicMock

from kash.exec.precondition_checks import actions_matching_paths, items_matching_precondition
from kash.model.items_model import Item, ItemType
from kash.model.paths_model import StorePath
from kash.model.preconditions_model import Precondition
from kash.utils.file_utils.file_formats_model import Format


def _mock_ws_with_items(items_by_path: dict[str, Item]) -> MagicMock:
    ws = MagicMock()
    ws.load.side_effect = lambda sp: items_by_path[str(sp)]
    ws.walk_items.return_value = [StorePath(p) for p in items_by_path]
    return ws


def _item(title: str, item_type: ItemType = ItemType.doc, fmt: Format = Format.markdown) -> Item:
    return Item(title=title, type=item_type, format=fmt, body="content")


class TestActionsMatchingPaths:
    def test_action_with_matching_precondition(self):
        """Actions whose precondition passes for all paths are yielded."""
        item = _item("Test")
        ws = _mock_ws_with_items({"a.doc.md": item})
        action = MagicMock()
        action.precondition = Precondition(lambda i: i.type == ItemType.doc)
        result = list(actions_matching_paths([action], ws, [StorePath("a.doc.md")]))
        assert result == [action]

    def test_action_with_failing_precondition(self):
        """Actions whose precondition fails are excluded."""
        item = _item("Test", item_type=ItemType.resource)
        ws = _mock_ws_with_items({"a.resource.md": item})
        action = MagicMock()
        action.precondition = Precondition(lambda i: i.type == ItemType.doc)
        result = list(actions_matching_paths([action], ws, [StorePath("a.resource.md")]))
        assert result == []

    def test_action_without_precondition_excluded_by_default(self):
        """Actions with no precondition are excluded unless include_no_precondition=True."""
        ws = _mock_ws_with_items({"a.doc.md": _item("Test")})
        action = MagicMock()
        action.precondition = None
        assert list(actions_matching_paths([action], ws, [StorePath("a.doc.md")])) == []

    def test_action_without_precondition_included_when_flag_set(self):
        """Actions with no precondition are included when flag is set."""
        ws = _mock_ws_with_items({"a.doc.md": _item("Test")})
        action = MagicMock()
        action.precondition = None
        result = list(
            actions_matching_paths(
                [action], ws, [StorePath("a.doc.md")], include_no_precondition=True
            )
        )
        assert result == [action]

    def test_multiple_paths_all_must_match(self):
        """Precondition must pass for ALL paths."""
        doc_item = _item("Doc", ItemType.doc)
        res_item = _item("Res", ItemType.resource)
        ws = _mock_ws_with_items({"a.doc.md": doc_item, "b.resource.md": res_item})
        action = MagicMock()
        action.precondition = Precondition(lambda i: i.type == ItemType.doc)
        result = list(
            actions_matching_paths(
                [action], ws, [StorePath("a.doc.md"), StorePath("b.resource.md")]
            )
        )
        assert result == []


class TestItemsMatchingPrecondition:
    def test_returns_matching_items(self):
        """Yields items that satisfy the precondition."""
        items = {"a.doc.md": _item("A"), "b.doc.md": _item("B")}
        ws = _mock_ws_with_items(items)
        precondition = Precondition(lambda i: True)
        result = list(items_matching_precondition(ws, precondition))
        assert len(result) == 2

    def test_filters_non_matching(self):
        """Only yields items where precondition returns True."""
        items = {
            "a.doc.md": _item("A", ItemType.doc),
            "b.resource.md": _item("B", ItemType.resource),
        }
        ws = _mock_ws_with_items(items)
        precondition = Precondition(lambda i: i.type == ItemType.doc)
        result = list(items_matching_precondition(ws, precondition))
        assert len(result) == 1
        assert result[0].title == "A"

    def test_max_results_limits_output(self):
        """Respects max_results limit."""
        items = {f"{i}.doc.md": _item(f"Item{i}") for i in range(10)}
        ws = _mock_ws_with_items(items)
        precondition = Precondition(lambda i: True)
        result = list(items_matching_precondition(ws, precondition, max_results=3))
        assert len(result) == 3

    def test_skippable_errors_are_skipped(self):
        """Items that raise SkippableError on load are silently skipped."""
        from kash.utils.errors import SkippableError

        ws = MagicMock()
        ws.walk_items.return_value = [StorePath("bad.doc.md"), StorePath("good.doc.md")]
        ws.load.side_effect = [SkippableError("broken"), _item("Good")]
        precondition = Precondition(lambda i: True)
        result = list(items_matching_precondition(ws, precondition))
        assert len(result) == 1
        assert result[0].title == "Good"
