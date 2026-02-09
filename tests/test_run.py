"""
Tests for kash.run standalone action runner.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from kash.model.actions_model import Action, ActionResult
from kash.model.items_model import Item, ItemType
from kash.run import _build_action_input, _resolve_workspace_dir, kash_run
from kash.utils.file_utils.file_formats_model import Format


def test_build_action_input_empty():
    result = _build_action_input(None, Path("/tmp"))
    assert result.items == []


def test_build_action_input_empty_list():
    result = _build_action_input([], Path("/tmp"))
    assert result.items == []


def test_build_action_input_url():
    result = _build_action_input(["https://example.com"], Path("/tmp"))
    assert len(result.items) == 1
    assert result.items[0].url == "https://example.com"
    assert result.items[0].type == ItemType.resource


def test_build_action_input_file(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("hello world")
    result = _build_action_input([str(f)], Path("/tmp"))
    assert len(result.items) == 1
    assert result.items[0].body == "hello world"
    assert result.items[0].type == ItemType.doc


def test_build_action_input_item():
    item = Item(type=ItemType.doc, title="test", body="content", format=Format.markdown)
    result = _build_action_input([item], Path("/tmp"))
    assert len(result.items) == 1
    assert result.items[0] is item


def test_build_action_input_mixed(tmp_path):
    f = tmp_path / "test.md"
    f.write_text("# Hello")
    item = Item(type=ItemType.doc, title="existing", body="body", format=Format.markdown)
    result = _build_action_input(
        ["https://example.com", str(f), item],
        Path("/tmp"),
    )
    assert len(result.items) == 3
    assert result.items[0].url == "https://example.com"
    assert result.items[1].body == "# Hello"
    assert result.items[2] is item


def test_build_action_input_file_not_found():
    import pytest

    with pytest.raises(Exception, match="not found"):
        _build_action_input(["/nonexistent/file.txt"], Path("/tmp"))


def test_resolve_workspace_dir_explicit(tmp_path):
    ws = tmp_path / "my_ws"
    result = _resolve_workspace_dir(ws)
    assert result == ws
    assert ws.is_dir()


def test_resolve_workspace_dir_creates_dir(tmp_path):
    ws = tmp_path / "new" / "workspace"
    result = _resolve_workspace_dir(ws)
    assert result == ws
    assert ws.is_dir()


def test_resolve_workspace_dir_fallback_temp():
    with patch("kash.workspaces.workspace_dirs.enclosing_ws_dir", return_value=None):
        result = _resolve_workspace_dir(None)
        assert "kash_run_" in str(result)
        assert result.is_dir()


def test_kash_run_with_mock_action(tmp_path):
    """Test the full kash_run pipeline with a mocked action."""
    output_item = Item(
        type=ItemType.doc,
        title="Result",
        body="Processed content",
        format=Format.markdown,
    )
    mock_result = ActionResult(items=[output_item])

    # Create a mock action class.
    mock_action = MagicMock(spec=Action)
    mock_action.name = "test_action"
    mock_action.run_per_item = False
    mock_action.cacheable = False
    mock_action.run.return_value = mock_result
    mock_action.validate_args.return_value = None
    mock_action.validate_params_present.return_value = None
    mock_action.validate_precondition.return_value = None
    mock_action.param_value_summary.return_value = {}
    mock_action.expected_args = None
    mock_action.params = []

    mock_action_cls = MagicMock()
    mock_action_cls.create.return_value = mock_action

    with (
        patch("kash.run.look_up_action_class", return_value=mock_action_cls),
        patch("kash.run.save_action_result", new=MagicMock()),
    ):
        result = kash_run(
            "test_action",
            workspace_dir=tmp_path,
        )

    assert result.items == [output_item]
    assert result.items[0].body == "Processed content"


def test_kash_run_with_inputs(tmp_path):
    """Test kash_run passes inputs through correctly."""
    output_item = Item(
        type=ItemType.doc,
        title="Result",
        body="Extracted text",
        format=Format.markdown,
    )

    mock_action = MagicMock(spec=Action)
    mock_action.name = "strip_html"
    mock_action.run_per_item = False
    mock_action.cacheable = False
    mock_action.run.return_value = ActionResult(items=[output_item])
    mock_action.validate_args.return_value = None
    mock_action.validate_params_present.return_value = None
    mock_action.validate_precondition.return_value = None
    mock_action.param_value_summary.return_value = {}
    mock_action.expected_args = None
    mock_action.params = []

    mock_action_cls = MagicMock()
    mock_action_cls.create.return_value = mock_action

    with (
        patch("kash.run.look_up_action_class", return_value=mock_action_cls),
        patch("kash.run.save_action_result", new=MagicMock()),
    ):
        result = kash_run(
            "strip_html",
            inputs=["https://example.com"],
            workspace_dir=tmp_path,
        )

    # Verify action was called with an ActionInput containing our URL.
    call_args = mock_action.run.call_args
    action_input = call_args[0][0]
    assert len(action_input.items) == 1
    assert action_input.items[0].url == "https://example.com"
    assert result.items[0].body == "Extracted text"


def test_kash_run_no_save(tmp_path):
    """Test kash_run with save_results=False skips saving."""
    output_item = Item(type=ItemType.doc, title="r", body="b", format=Format.markdown)

    mock_action = MagicMock(spec=Action)
    mock_action.name = "test_action"
    mock_action.run_per_item = False
    mock_action.cacheable = False
    mock_action.run.return_value = ActionResult(items=[output_item])
    mock_action.validate_args.return_value = None
    mock_action.validate_params_present.return_value = None
    mock_action.validate_precondition.return_value = None
    mock_action.param_value_summary.return_value = {}
    mock_action.expected_args = None
    mock_action.params = []

    mock_action_cls = MagicMock()
    mock_action_cls.create.return_value = mock_action

    mock_save = MagicMock()
    with (
        patch("kash.run.look_up_action_class", return_value=mock_action_cls),
        patch("kash.run.save_action_result", mock_save),
    ):
        kash_run("test_action", workspace_dir=tmp_path, save_results=False)

    mock_save.assert_not_called()
