"""Tests for ItemType and Item model pure functions."""

from __future__ import annotations

from kash.model.items_model import Item, ItemType
from kash.utils.file_utils.file_formats_model import FileExt, Format


def test_item_type_expects_body():
    assert ItemType.doc.expects_body
    assert ItemType.export.expects_body
    assert not ItemType.resource.expects_body
    assert not ItemType.concept.expects_body


def test_item_type_allows_op_suffix():
    assert ItemType.doc.allows_op_suffix
    assert not ItemType.resource.allows_op_suffix
    assert not ItemType.concept.allows_op_suffix
    assert not ItemType.export.allows_op_suffix


def test_item_type_for_format():
    assert ItemType.for_format(Format.markdown) == ItemType.doc
    assert ItemType.for_format(Format.html) == ItemType.doc
    assert ItemType.for_format(Format.pdf) == ItemType.resource
    assert ItemType.for_format(Format.png) == ItemType.asset
    assert ItemType.for_format(Format.csv) == ItemType.table


def test_item_content_equals():
    item1 = Item(title="Test", type=ItemType.doc, format=Format.markdown, body="Hello")
    item2 = Item(title="Test", type=ItemType.doc, format=Format.markdown, body="Hello")
    item3 = Item(title="Test", type=ItemType.doc, format=Format.markdown, body="Different")

    assert item1.content_equals(item2)
    assert not item1.content_equals(item3)


def test_item_full_text():
    item = Item(
        title="My Title",
        description="A description",
        type=ItemType.doc,
        format=Format.markdown,
        body="Body content here.",
    )
    full = item.full_text()
    assert "My Title" in full
    assert "A description" in full
    assert "Body content here." in full


def test_item_body_text_validates():
    """Binary format items should raise on body_text()."""
    item = Item(title="Image", type=ItemType.asset, format=Format.png)
    try:
        item.body_text()
        raise AssertionError("Expected error for binary format")
    except Exception:
        pass


def test_item_get_file_ext():
    item = Item(title="Test", type=ItemType.doc, format=Format.markdown)
    ext = item.get_file_ext()
    assert ext == FileExt.md


def test_item_slug_name():
    item = Item(title="My Great Document!", type=ItemType.doc, format=Format.markdown)
    slug = item.slug_name()
    assert slug
    assert " " not in slug
    # Slug should be lowercase and contain no special chars
    assert slug == slug.lower() or "_" in slug


def test_item_new_copy_with():
    item = Item(
        title="Original",
        type=ItemType.doc,
        format=Format.markdown,
        body="Original body",
    )
    copied = item.new_copy_with(title="Updated")
    assert copied.title == "Updated"
    assert copied.body == "Original body"
    assert item.title == "Original"  # original unchanged


def test_item_metadata_round_trip():
    """Metadata serialization should produce a dict that can reconstruct the Item."""
    item = Item(
        title="Test Item",
        type=ItemType.doc,
        format=Format.markdown,
        body="# Hello\n\nWorld",
        description="A test item",
    )
    meta = item.metadata()
    assert meta["title"] == "Test Item"
    assert meta["type"] == "doc"
    assert meta["format"] == "markdown"

    # Reconstruct from metadata
    reconstructed = Item.from_dict(meta)
    assert reconstructed.title == item.title
    assert reconstructed.type == item.type
    assert reconstructed.format == item.format
