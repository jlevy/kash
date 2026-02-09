"""Tests for selections: Selection and SelectionHistory state management."""

from __future__ import annotations

import pytest

from kash.model.paths_model import StorePath
from kash.utils.errors import InvalidOperation
from kash.workspaces.selections import Selection, SelectionHistory


@pytest.fixture
def history(tmp_path) -> SelectionHistory:
    """Create a SelectionHistory with a temp save file."""
    return SelectionHistory.init(tmp_path / "selections.yml")


class TestSelection:
    def test_empty_is_falsy(self):
        sel = Selection(paths=[])
        assert not sel

    def test_non_empty_is_truthy(self):
        sel = Selection(paths=[StorePath("a.doc.md")])
        assert sel

    def test_clear(self):
        sel = Selection(paths=[StorePath("a.doc.md"), StorePath("b.doc.md")])
        sel.clear()
        assert sel.paths == []

    def test_remove_values(self):
        sel = Selection(paths=[StorePath("a.doc.md"), StorePath("b.doc.md"), StorePath("c.doc.md")])
        sel.remove_values([StorePath("b.doc.md")])
        assert sel.paths == [StorePath("a.doc.md"), StorePath("c.doc.md")]

    def test_replace_values(self):
        sel = Selection(paths=[StorePath("old.doc.md")])
        sel.replace_values([(StorePath("old.doc.md"), StorePath("new.doc.md"))])
        assert sel.paths == [StorePath("new.doc.md")]

    def test_refresh_drops_missing(self, tmp_path):
        """refresh() removes paths that don't exist on disk."""
        (tmp_path / "exists.doc.md").touch()
        sel = Selection(paths=[StorePath("exists.doc.md"), StorePath("gone.doc.md")])
        sel.refresh(tmp_path)
        assert sel.paths == [StorePath("exists.doc.md")]


class TestSelectionHistory:
    def test_current_empty_when_no_history(self, history):
        assert not history.current
        assert history.current.paths == []

    def test_push_and_current(self, history):
        history.push(Selection(paths=[StorePath("a.doc.md")]))
        assert history.current.paths == [StorePath("a.doc.md")]

    def test_push_ignores_empty(self, history):
        history.push(Selection(paths=[]))
        assert len(history.history) == 0

    def test_push_ignores_duplicate(self, history):
        sel = Selection(paths=[StorePath("a.doc.md")])
        history.push(sel)
        history.push(Selection(paths=[StorePath("a.doc.md")]))
        assert len(history.history) == 1

    def test_previous_and_next(self, history):
        history.push(Selection(paths=[StorePath("a.doc.md")]))
        history.push(Selection(paths=[StorePath("b.doc.md")]))
        prev = history.previous()
        assert prev.paths == [StorePath("a.doc.md")]
        nxt = history.next()
        assert nxt.paths == [StorePath("b.doc.md")]

    def test_previous_at_start_raises(self, history):
        history.push(Selection(paths=[StorePath("a.doc.md")]))
        with pytest.raises(InvalidOperation, match="No previous"):
            history.previous()

    def test_next_at_end_raises(self, history):
        history.push(Selection(paths=[StorePath("a.doc.md")]))
        with pytest.raises(InvalidOperation, match="No next"):
            history.next()

    def test_pop(self, history):
        history.push(Selection(paths=[StorePath("a.doc.md")]))
        popped = history.pop()
        assert popped.paths == [StorePath("a.doc.md")]
        assert len(history.history) == 0

    def test_pop_empty_raises(self, history):
        with pytest.raises(InvalidOperation, match="No current"):
            history.pop()

    def test_clear_all(self, history):
        history.push(Selection(paths=[StorePath("a.doc.md")]))
        history.push(Selection(paths=[StorePath("b.doc.md")]))
        history.clear_all()
        assert len(history.history) == 0

    def test_persistence(self, tmp_path):
        """History persists to disk and can be reloaded."""
        save_path = tmp_path / "sel.yml"
        h1 = SelectionHistory.init(save_path)
        h1.push(Selection(paths=[StorePath("a.doc.md")]))
        # Reload from disk
        h2 = SelectionHistory.init(save_path)
        assert h2.current.paths == [StorePath("a.doc.md")]

    def test_truncation(self, tmp_path):
        """History truncates beyond max_history."""
        h = SelectionHistory.init(tmp_path / "sel.yml", max_history=3)
        for i in range(5):
            h.push(Selection(paths=[StorePath(f"{i}.doc.md")]))
        assert len(h.history) <= 3

    def test_set_current(self, history):
        history.push(Selection(paths=[StorePath("a.doc.md")]))
        history.set_current([StorePath("b.doc.md")])
        assert history.current.paths == [StorePath("b.doc.md")]

    def test_unselect_current(self, history):
        history.push(Selection(paths=[StorePath("a.doc.md"), StorePath("b.doc.md")]))
        result = history.unselect_current([StorePath("a.doc.md")])
        assert result.paths == [StorePath("b.doc.md")]
