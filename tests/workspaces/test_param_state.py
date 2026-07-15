"""Tests for param_state: ParamState persistence and retrieval."""

from __future__ import annotations

from kash.model.params_model import RawParamValues
from kash.workspaces.param_state import ParamState


class TestParamState:
    def test_set_and_get(self, tmp_path):
        """Can set parameters and retrieve them."""
        ps = ParamState(tmp_path / "params.yml")
        ps.set({"model": "gpt-5.6-terra", "language": "en"})
        result = ps.get_raw_values()
        assert isinstance(result, RawParamValues)
        assert result.values.get("model") == "gpt-5.6-terra"
        assert result.values.get("language") == "en"

    def test_get_missing_file_returns_empty(self, tmp_path):
        """When file doesn't exist, returns empty RawParamValues."""
        ps = ParamState(tmp_path / "nonexistent.yml")
        result = ps.get_raw_values()
        assert isinstance(result, RawParamValues)
        assert len(result.values) == 0

    def test_overwrite(self, tmp_path):
        """Setting new values overwrites previous ones."""
        ps = ParamState(tmp_path / "params.yml")
        ps.set({"model": "gpt-5.6-terra"})
        ps.set({"model": "claude-sonnet-5"})
        result = ps.get_raw_values()
        assert result.values.get("model") == "claude-sonnet-5"

    def test_persistence_across_instances(self, tmp_path):
        """Data persists across ParamState instances."""
        path = tmp_path / "params.yml"
        ps1 = ParamState(path)
        ps1.set({"query": "test"})
        ps2 = ParamState(path)
        result = ps2.get_raw_values()
        assert result.values.get("query") == "test"
