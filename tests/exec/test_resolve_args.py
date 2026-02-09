"""Tests for resolve_args: path/URL resolution, selection fallback."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from kash.exec.resolve_args import (
    assemble_action_args,
    assemble_path_args,
    resolve_locator_arg,
    resolve_path_arg,
)
from kash.model.paths_model import StorePath
from kash.utils.common.url import Url
from kash.utils.errors import InvalidInput, MissingInput


class TestResolveLocatorArg:
    def test_store_path_passthrough(self):
        """A StorePath argument is returned as-is."""
        sp = StorePath("some/path.doc.md")
        result = resolve_locator_arg(sp)
        assert result is sp

    def test_url_returns_url(self):
        """A URL string is returned as a Url (str)."""
        result = resolve_locator_arg("https://example.com/page")
        assert result == "https://example.com/page"
        assert isinstance(result, str)

    def test_plain_path_resolves(self):
        """A non-URL string delegates to resolve_path_arg."""
        with patch("kash.exec.resolve_args.resolve_path_arg", return_value=Path("/tmp/file")) as m:
            result = resolve_locator_arg("file.txt")
            m.assert_called_once_with("file.txt")
            assert result == Path("/tmp/file")


class TestResolvePathArg:
    def test_url_raises(self):
        """A URL string raises InvalidInput."""
        with pytest.raises(InvalidInput, match="Expected a path but got a URL"):
            resolve_path_arg("https://example.com")

    def test_absolute_path(self):
        """An absolute path is returned directly."""
        result = resolve_path_arg("/tmp/absolute/file.txt")
        assert result == Path("/tmp/absolute/file.txt")

    def test_relative_resolves_to_store_path(self):
        """A relative path resolves to StorePath via workspace."""
        mock_ws = MagicMock()
        sp = StorePath("resolved.doc.md")
        mock_ws.resolve_to_store_path.return_value = sp
        with patch("kash.exec.resolve_args.current_ws", return_value=mock_ws):
            result = resolve_path_arg("resolved.doc.md")
            assert result == sp


class TestAssembleActionArgs:
    def test_with_explicit_args(self):
        """Explicit args are resolved and returned; selection not used."""
        with patch(
            "kash.exec.resolve_args.resolve_locator_arg",
            side_effect=lambda x: Url(x),
        ):
            args, from_sel = assemble_action_args(
                "https://a.com", "https://b.com", use_selection=True
            )
            assert len(args) == 2
            assert from_sel is False

    def test_fallback_to_selection(self):
        """When no args given, falls back to current selection."""
        mock_ws = MagicMock()
        mock_ws.selections.current.paths = [StorePath("sel.doc.md")]
        with patch("kash.exec.resolve_args.current_ws", return_value=mock_ws):
            args, from_sel = assemble_action_args(use_selection=True)
            assert len(args) == 1
            assert from_sel is True

    def test_no_selection_returns_empty(self):
        """When selection is empty and no args, returns empty list."""
        mock_ws = MagicMock()
        mock_ws.selections.current.paths.__iter__ = MagicMock(
            side_effect=MissingInput("No selection")
        )
        # Simulate MissingInput being raised
        type(mock_ws.selections.current).paths = property(
            lambda self: (_ for _ in ()).throw(MissingInput("No selection"))
        )
        with patch("kash.exec.resolve_args.current_ws", return_value=mock_ws):
            args, from_sel = assemble_action_args(use_selection=True)
            assert args == []
            assert from_sel is False


class TestAssemblePathArgs:
    def test_with_args(self):
        """Explicit paths are resolved."""
        with patch(
            "kash.exec.resolve_args.resolve_path_arg",
            return_value=StorePath("a.doc.md"),
        ):
            result = assemble_path_args("a.doc.md")
            assert len(result) == 1

    def test_fallback_to_selection(self):
        """Falls back to workspace selection when no args."""
        mock_ws = MagicMock()
        mock_ws.selections.current.paths = [StorePath("sel.doc.md")]
        with patch("kash.exec.resolve_args.current_ws", return_value=mock_ws):
            result = assemble_path_args()
            assert result == [StorePath("sel.doc.md")]

    def test_no_selection_raises(self):
        """Raises MissingInput when no args and no selection."""
        mock_ws = MagicMock()
        mock_ws.selections.current.paths = []
        with patch("kash.exec.resolve_args.current_ws", return_value=mock_ws):
            with pytest.raises(MissingInput, match="No selection"):
                assemble_path_args()
