from __future__ import annotations

import re
from datetime import UTC, date, datetime, time
from pathlib import Path

from frontmatter_format import from_yaml_string, to_yaml_string
from sidematter_format import register_default_yaml_representers, to_json_string

from kash.file_storage.item_file_format import read_item, write_item
from kash.model.items_model import Item, ItemType
from kash.utils.file_utils.file_formats_model import FileExt, Format

# Ensure YAML representers are registered for the test process
register_default_yaml_representers()


def test_json_serializes_dates_and_enums() -> None:
    now = datetime(2024, 1, 2, 3, 4, 5, tzinfo=UTC)
    d = {
        "when": now,
        "day": date(2024, 1, 2),
        "clock": time(3, 4, 5),
        "kind": ItemType.doc,
    }

    js = to_json_string(d)
    assert re.search(r"2024-01-02T03:04:05(\.\d+)?Z", js)
    assert "2024-01-02" in js
    assert "03:04:05" in js
    assert '"doc"' in js


def test_yaml_serializes_dates_and_enums() -> None:
    now = datetime(2024, 1, 2, 3, 4, 5, tzinfo=UTC)
    d = {
        "when": now,
        "day": date(2024, 1, 2),
        "clock": time(3, 4, 5),
        "kind": ItemType.doc,
    }

    ys = to_yaml_string(d)
    # Represented as strings per project policy
    assert re.search(r"2024-01-02T03:04:05(\.\d+)?Z", ys)
    assert "2024-01-02" in ys
    assert "03:04:05" in ys
    assert "doc" in ys

    roundtrip = from_yaml_string(ys)
    # ruamel will load them as strings under our representers (allow optional fractional seconds)
    assert re.fullmatch(r"2024-01-02T03:04:05(\.\d+)?Z", roundtrip["when"]) is not None
    assert roundtrip["day"] == "2024-01-02"
    assert roundtrip["clock"] == "03:04:05"
    assert roundtrip["kind"] == "doc"


def test_item_metadata_yaml_and_json_roundtrip() -> None:
    created = datetime(2024, 6, 7, 12, 34, 56, tzinfo=UTC)
    item = Item(type=ItemType.doc, title="Hello", created_at=created)
    meta = item.metadata()

    # JSON: uses our defaults
    js = to_json_string(meta)
    assert "2024-06-07" in js

    # YAML: via frontmatter_format, with our representers registered
    ys = to_yaml_string(meta)
    assert "2024-06-07" in ys

    # Round-trip YAML to Python dict
    round_meta = from_yaml_string(ys)
    # created_at will be a string per representer policy
    assert isinstance(round_meta, dict)
    assert "created_at" in round_meta


def _new_item_with_dt() -> Item:
    created = datetime(2024, 7, 8, 9, 10, 11, 123456, tzinfo=UTC)
    return Item(
        type=ItemType.doc,
        title="DT Roundtrip",
        format=Format.markdown,
        file_ext=FileExt.md,
        created_at=created,
        body="# Title\n\nBody text.\n",
    )


def test_frontmatter_roundtrip_preserves_created_at(tmp_path: Path) -> None:
    item = _new_item_with_dt()
    path = tmp_path / "doc_frontmatter.doc.md"
    write_item(item, path, normalize=False, use_frontmatter=True)

    loaded = read_item(path, tmp_path)

    assert isinstance(loaded.created_at, datetime)
    assert loaded.created_at == item.created_at
    # modified_at can be None if mtime equals created time; tolerate that
    assert loaded.modified_at is None or isinstance(loaded.modified_at, datetime)


def test_sidematter_roundtrip_preserves_created_at(tmp_path: Path) -> None:
    item = _new_item_with_dt()
    path = tmp_path / "doc_sidematter.doc.md"
    write_item(item, path, normalize=False, use_frontmatter=False)

    loaded = read_item(path, tmp_path)

    assert isinstance(loaded.created_at, datetime)
    assert loaded.created_at == item.created_at
    assert loaded.modified_at is None or isinstance(loaded.modified_at, datetime)
