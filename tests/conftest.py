"""
Shared test fixtures for kash tests.

Provides workspace, LLM, and item fixtures per the test infrastructure spec.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from kash.model.items_model import Item, ItemType
from kash.utils.file_utils.file_formats_model import Format


@pytest.fixture
def temp_workspace(tmp_path):
    """Create a temporary kash workspace for testing."""
    ws_dir = tmp_path / "test_workspace"
    ws_dir.mkdir()
    from kash.file_storage.file_store import FileStore

    return FileStore(ws_dir, is_global_ws=False, auto_init=True)


@pytest.fixture
def mock_current_ws(temp_workspace):
    """Patch `current_ws()` to return the temp workspace."""
    with patch("kash.workspaces.workspaces.current_ws", return_value=temp_workspace):
        yield temp_workspace


@pytest.fixture
def mock_llm():
    """Mock LLM API calls for deterministic testing."""
    with patch("kash.llm_utils.llm_completion.litellm.completion") as mock:
        mock.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="mocked response"))],
            usage=MagicMock(prompt_tokens=10, completion_tokens=20),
        )
        yield mock


@pytest.fixture
def sample_item():
    """Create a minimal Item for testing."""
    return Item(
        title="Test Item",
        type=ItemType.doc,
        format=Format.markdown,
        body="# Test\n\nThis is test content.",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "online: marks tests that need network access")
    config.addinivalue_line("markers", "golden: marks golden/snapshot tests")
