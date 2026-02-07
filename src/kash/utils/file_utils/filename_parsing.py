from __future__ import annotations

import os
import re
from pathlib import Path

from kash.config.logger import get_logger
from kash.utils.common.url import Url, check_if_url
from kash.utils.file_utils.file_ext import FileExt, canonicalize_file_ext

log = get_logger(__name__)

_valid_ext_re = re.compile(r"^[a-z0-9]*[a-z][a-z0-9]*$", re.IGNORECASE)


def split_filename(path: str | Path) -> tuple[str, str, str, str]:
    """
    Parse a filename into its path, name, (optional) type, and extension parts.
    Type and extension are optional but must be only letters/numbers and not
    all numbers.

    folder/file.name.type.ext -> ("folder", "file.name", "type", "ext")
    filename.doc.txt -> ("", "filename", "note", "txt")
    filename.txt -> ("", "filename", "", "txt")
    filename -> ("", "filename", "", "")
    filename.123.txt -> ("", "filename.123", "", "txt")
    filename.123.456 -> ("", "filename.123.456", "", "")
    """
    path_str = str(path)

    dirname = os.path.dirname(path_str)
    parts = os.path.basename(path_str).rsplit(".", 2)
    if len(parts) == 3 and _valid_ext_re.match(parts[1]) and _valid_ext_re.match(parts[2]):
        name, item_type, ext = parts
    elif len(parts) == 3 and _valid_ext_re.match(parts[2]):
        name = f"{parts[0]}.{parts[1]}"
        item_type = ""
        ext = parts[2]
    elif len(parts) == 2 and _valid_ext_re.match(parts[1]):
        name, ext = parts
        item_type = ""
    else:
        name = os.path.basename(path_str)
        item_type = ext = ""

    return dirname, name, item_type, ext


def join_filename(dirname: str | Path, name: str, item_type: str | None, ext: str) -> Path:
    """
    Join a filename into a single path, with optional type and extension.
    """

    parts: list[str] = list(filter(bool, [name, item_type, ext]))  # pyright: ignore
    return Path(dirname) / ".".join(parts)


def parse_file_ext(url_or_path: str | Url | Path) -> FileExt | None:
    """
    Parse a known, canonical file extension from a path or URL. Also accepts
    raw file extensions (like "csv" or ".csv").
    """
    parsed_url = check_if_url(url_or_path)
    if parsed_url:
        path = parsed_url.path
    else:
        path = str(url_or_path)
    front, ext = os.path.splitext(path.split("/")[-1])
    if not ext:
        # Handle bare file extensions too.
        ext = front
    return FileExt.parse(canonicalize_file_ext(ext))


## Tests


def test_parse_filename():
    filename = "foo/bar/test_file.1.type.ext"
    dirname, name, item_type, ext = split_filename(filename)
    assert dirname == "foo/bar"
    assert name == "test_file.1"
    assert item_type == "type"
    assert ext == "ext"

    filename = "foo/bar/test_file.ext"
    dirname, name, item_type, ext = split_filename(filename)
    assert dirname == "foo/bar"
    assert name == "test_file"
    assert item_type == ""
    assert ext == "ext"

    filename = "test_file"
    dirname, name, item_type, ext = split_filename(filename)
    assert dirname == ""
    assert name == "test_file"
    assert item_type == ""
    assert ext == ""

    # Numeric extensions not allowed.
    dirname, name, item_type, ext = split_filename("test.abc")
    assert name == "test"
    assert ext == "abc"

    dirname, name, item_type, ext = split_filename("test.123")
    assert name == "test.123"
    assert ext == ""

    dirname, name, item_type, ext = split_filename("test.type.123")
    assert name == "test.type.123"
    assert item_type == ""
    assert ext == ""

    dirname, name, item_type, ext = split_filename("test.valid.123")
    assert name == "test.valid.123"
    assert item_type == ""
    assert ext == ""

    dirname, name, item_type, ext = split_filename("test.123.txt")
    assert name == "test.123"
    assert item_type == ""
    assert ext == "txt"


def test_parse_file_ext():
    assert parse_file_ext("test.md") == FileExt.md
    assert parse_file_ext("test.resource.md") == FileExt.md
    assert parse_file_ext(".md") == FileExt.md
    assert parse_file_ext("md") == FileExt.md
    assert parse_file_ext("foobar") is None
    assert parse_file_ext(Url("http://example.com/test.md")) == FileExt.md
    assert parse_file_ext(Url("http://example.com/test")) is None
