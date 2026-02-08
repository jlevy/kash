"""Tests for action_registry: registration, lookup, caching."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from kash.exec.action_registry import (
    action_classes,
    clear_action_cache,
    look_up_action_class,
    register_action_class,
)
from kash.model.actions_model import Action, ActionInput, ActionResult
from kash.utils.errors import InvalidInput


def _make_action_class(name: str) -> type[Action]:
    """Create a minimal mock action class for testing."""
    cls = MagicMock(spec=Action)
    cls.name = name
    cls.create = MagicMock(return_value=MagicMock(name=name))
    return cls  # type: ignore[return-value]  # pyright: ignore[reportReturnType]


class TestRegisterActionClass:
    def test_registers_new_action(self):
        """Registering a class adds it to the global registry."""
        cls = _make_action_class("test_reg_action")
        original = action_classes.copy()
        try:
            register_action_class(cls)
            assert action_classes.copy()["test_reg_action"] is cls
        finally:
            # Restore original state.
            with action_classes.updates() as ac:
                ac.clear()
                ac.update(original)
            clear_action_cache()

    def test_duplicate_warns(self, caplog):
        """Registering the same action name twice logs a warning."""
        cls1 = _make_action_class("test_dup_action")
        cls2 = _make_action_class("test_dup_action")
        original = action_classes.copy()
        try:
            register_action_class(cls1)
            register_action_class(cls2)
            assert "Duplicate action name" in caplog.text
        finally:
            with action_classes.updates() as ac:
                ac.clear()
                ac.update(original)
            clear_action_cache()


class TestLookUpActionClass:
    def test_found(self):
        """Looking up a registered action returns its class."""
        cls = _make_action_class("test_lookup_action")
        with patch(
            "kash.exec.action_registry.get_all_action_classes",
            return_value={"test_lookup_action": cls},
        ):
            assert look_up_action_class("test_lookup_action") is cls

    def test_not_found_raises(self):
        """Looking up a missing action raises InvalidInput."""
        with patch(
            "kash.exec.action_registry.get_all_action_classes",
            return_value={},
        ):
            with pytest.raises(InvalidInput, match="Action not found"):
                look_up_action_class("no_such_action")
