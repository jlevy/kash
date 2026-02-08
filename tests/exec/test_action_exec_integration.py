"""
Integration tests for the action execution pipeline.

Tests the full kash_run() pipeline with mocked actions and workspaces,
verifying that input resolution, validation, execution, and result
handling all work together.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from kash.exec_model.args_model import NO_ARGS, ONE_OR_MORE_ARGS
from kash.model.actions_model import (
    Action,
    ActionInput,
    ActionResult,
)
from kash.model.items_model import Item, ItemType
from kash.model.preconditions_model import Precondition
from kash.run import kash_run
from kash.utils.file_utils.file_formats_model import Format


def _make_mock_action(
    name: str = "test_action",
    *,
    output_body: str = "result",
    run_per_item: bool = False,
    expected_args=ONE_OR_MORE_ARGS,
) -> MagicMock:
    """Create a mock action that returns a single output item."""
    output_item = Item(
        type=ItemType.doc,
        title="Output",
        body=output_body,
        format=Format.markdown,
    )

    mock_action = MagicMock(spec=Action)
    mock_action.name = name
    mock_action.run_per_item = run_per_item
    mock_action.cacheable = False
    mock_action.expected_args = expected_args
    mock_action.params = []
    mock_action.run.return_value = ActionResult(items=[output_item])
    mock_action.validate_args.return_value = None
    mock_action.validate_params_present.return_value = None
    mock_action.validate_precondition.return_value = None
    mock_action.param_value_summary.return_value = {}

    mock_cls = MagicMock()
    mock_cls.create.return_value = mock_action
    return mock_cls


class TestActionExecPipeline:
    """Integration tests exercising the full run pipeline."""

    def test_run_action_with_url_input(self, tmp_path):
        """Full pipeline: URL input -> action -> result items."""
        mock_cls = _make_mock_action("strip_html", output_body="clean text")

        with (
            patch("kash.run.look_up_action_class", return_value=mock_cls),
            patch("kash.run.save_action_result"),
        ):
            result = kash_run(
                "strip_html",
                inputs=["https://example.com/page.html"],
                workspace_dir=tmp_path,
            )

        assert len(result.items) == 1
        assert result.items[0].body == "clean text"
        # Verify action received the URL item.
        action_input = mock_cls.create.return_value.run.call_args[0][0]
        assert action_input.items[0].url == "https://example.com/page.html"

    def test_run_action_with_file_input(self, tmp_path):
        """Full pipeline: file path input -> reads file -> action -> result."""
        source = tmp_path / "input.md"
        source.write_text("# Original Content")

        mock_cls = _make_mock_action("process_doc", output_body="processed")

        with (
            patch("kash.run.look_up_action_class", return_value=mock_cls),
            patch("kash.run.save_action_result"),
        ):
            result = kash_run(
                "process_doc",
                inputs=[str(source)],
                workspace_dir=tmp_path,
            )

        assert result.items[0].body == "processed"
        # Verify file content was read into the input item.
        action_input = mock_cls.create.return_value.run.call_args[0][0]
        assert action_input.items[0].body == "# Original Content"

    def test_run_action_with_item_input(self, tmp_path):
        """Full pipeline: direct Item input -> action -> result."""
        input_item = Item(
            type=ItemType.doc,
            title="Direct Input",
            body="some content",
            format=Format.markdown,
        )

        mock_cls = _make_mock_action("transform")

        with (
            patch("kash.run.look_up_action_class", return_value=mock_cls),
            patch("kash.run.save_action_result"),
        ):
            result = kash_run(
                "transform",
                inputs=[input_item],
                workspace_dir=tmp_path,
            )

        assert len(result.items) == 1
        # Input item should be passed through directly.
        action_input = mock_cls.create.return_value.run.call_args[0][0]
        assert action_input.items[0] is input_item

    def test_run_action_multiple_inputs(self, tmp_path):
        """Pipeline handles multiple inputs of mixed types."""
        f = tmp_path / "doc.txt"
        f.write_text("file content")
        item = Item(type=ItemType.doc, title="pre-built", body="b", format=Format.markdown)

        # Action returns one output per input.
        outputs = [
            Item(type=ItemType.doc, title=f"out{i}", body=f"result{i}", format=Format.markdown)
            for i in range(3)
        ]

        mock_action = MagicMock(spec=Action)
        mock_action.name = "multi"
        mock_action.run_per_item = False
        mock_action.cacheable = False
        mock_action.expected_args = ONE_OR_MORE_ARGS
        mock_action.params = []
        mock_action.run.return_value = ActionResult(items=outputs)
        mock_action.validate_args.return_value = None
        mock_action.validate_params_present.return_value = None
        mock_action.validate_precondition.return_value = None
        mock_action.param_value_summary.return_value = {}

        mock_cls = MagicMock()
        mock_cls.create.return_value = mock_action

        with (
            patch("kash.run.look_up_action_class", return_value=mock_cls),
            patch("kash.run.save_action_result"),
        ):
            result = kash_run(
                "multi",
                inputs=["https://example.com", str(f), item],
                workspace_dir=tmp_path,
            )

        assert len(result.items) == 3
        action_input = mock_action.run.call_args[0][0]
        assert len(action_input.items) == 3

    def test_run_action_with_params(self, tmp_path):
        """Parameters are passed through to action creation."""
        mock_cls = _make_mock_action("summarize")

        with (
            patch("kash.run.look_up_action_class", return_value=mock_cls),
            patch("kash.run.save_action_result"),
        ):
            kash_run(
                "summarize",
                inputs=["https://example.com"],
                params={"model": "gpt-4o", "max_tokens": "500"},
                workspace_dir=tmp_path,
            )

        # Verify params were passed to create().
        create_args = mock_cls.create.call_args
        raw_params = create_args[0][0]
        assert raw_params is not None

    def test_run_action_not_found(self, tmp_path):
        """Requesting a non-existent action should raise InvalidInput."""
        from kash.utils.errors import InvalidInput

        with pytest.raises(InvalidInput, match="not found"):
            kash_run("nonexistent_action", workspace_dir=tmp_path)

    def test_run_action_no_inputs(self, tmp_path):
        """Actions that take no inputs should work."""
        mock_cls = _make_mock_action("generate", expected_args=NO_ARGS, output_body="generated")

        with (
            patch("kash.run.look_up_action_class", return_value=mock_cls),
            patch("kash.run.save_action_result"),
        ):
            result = kash_run("generate", workspace_dir=tmp_path)

        assert result.items[0].body == "generated"
        action_input = mock_cls.create.return_value.run.call_args[0][0]
        assert action_input.items == []
