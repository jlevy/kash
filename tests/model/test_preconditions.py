"""Tests for Precondition boolean algebra and composition."""

from __future__ import annotations

from kash.model.items_model import Item, ItemType
from kash.model.preconditions_model import Precondition
from kash.utils.errors import PreconditionFailure
from kash.utils.file_utils.file_formats_model import Format


def _make_item(**kwargs) -> Item:
    defaults = dict(title="test", type=ItemType.doc, format=Format.markdown)
    defaults.update(kwargs)
    return Item(**defaults)


def test_and_operator():
    has_body = Precondition(lambda item: item.body is not None, "has_body")
    is_doc = Precondition(lambda item: item.type == ItemType.doc, "is_doc")
    combined = has_body & is_doc

    assert combined(_make_item(body="hello"))
    assert not combined(_make_item(body=None))
    assert not combined(_make_item(body="hello", type=ItemType.resource))
    assert "has_body & is_doc" in combined.name


def test_or_operator():
    is_doc = Precondition(lambda item: item.type == ItemType.doc, "is_doc")
    is_resource = Precondition(lambda item: item.type == ItemType.resource, "is_resource")
    combined = is_doc | is_resource

    assert combined(_make_item(type=ItemType.doc))
    assert combined(_make_item(type=ItemType.resource))
    assert not combined(_make_item(type=ItemType.asset))
    assert "is_doc | is_resource" in combined.name


def test_invert_operator():
    is_doc = Precondition(lambda item: item.type == ItemType.doc, "is_doc")
    not_doc = ~is_doc

    assert not not_doc(_make_item(type=ItemType.doc))
    assert not_doc(_make_item(type=ItemType.resource))
    assert "~is_doc" in not_doc.name


def test_complex_composition():
    """Test chaining multiple operators: (A & B) | ~C."""
    has_body = Precondition(lambda item: item.body is not None, "has_body")
    is_doc = Precondition(lambda item: item.type == ItemType.doc, "is_doc")
    is_resource = Precondition(lambda item: item.type == ItemType.resource, "is_resource")

    combined = (has_body & is_doc) | ~is_resource

    # has_body AND is_doc => True
    assert combined(_make_item(body="hello", type=ItemType.doc))
    # NOT is_resource => True (it's an asset)
    assert combined(_make_item(type=ItemType.asset))
    # is_resource AND NOT (has_body AND is_doc) => False
    assert not combined(_make_item(body=None, type=ItemType.resource))


def test_and_all_empty():
    combined = Precondition.and_all()
    assert combined(_make_item())


def test_or_all_empty():
    combined = Precondition.or_all()
    assert not combined(_make_item())


def test_and_all_multiple():
    p1 = Precondition(lambda item: True, "true1")
    p2 = Precondition(lambda item: True, "true2")
    p3 = Precondition(lambda item: False, "false1")

    assert Precondition.and_all(p1, p2)(_make_item())
    assert not Precondition.and_all(p1, p2, p3)(_make_item())


def test_always_and_never():
    item = _make_item()
    assert Precondition.always(item)
    assert not Precondition.never(item)


def test_check_raises_on_failure():
    never = Precondition(lambda item: False, "never_true")
    item = _make_item()
    try:
        never.check(item)
        raise AssertionError("Expected PreconditionFailure")
    except PreconditionFailure:
        pass


def test_precondition_failure_suppressed_in_call():
    """A func that raises PreconditionFailure should return False, not raise."""
    def raising_func(item: Item) -> bool:
        raise PreconditionFailure("test failure")

    p = Precondition(raising_func, "raiser")
    assert not p(_make_item())
