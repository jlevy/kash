import os
from pathlib import Path

from kash.config.logger import get_logger
from kash.utils.common.url import Url
from kash.utils.errors import InvalidFilename
from kash.utils.file_utils.file_ext import FileExt, canonicalize_file_ext

log = get_logger(__name__)


def split_filename(path: str | Path, require_type_ext: bool = False) -> tuple[str, str, str, str]:
    """
    Parse a filename into its path, name, (optional) type, and extension parts:

    folder/file.name.type.ext -> ("folder", "file.name", "type", "ext")
    filename.doc.txt -> ("", "filename", "note", "txt")
    filename.txt -> ("", "filename", "", "txt")
    filename -> ("", "filename", "", "")
    """
    path_str = str(path)

    dirname = os.path.dirname(path_str)
    parts = os.path.basename(path_str).rsplit(".", 2)
    if len(parts) == 3:
        name, item_type, ext = parts
    elif len(parts) == 2 and not require_type_ext:
        name, ext = parts
        item_type = ""
    elif len(parts) == 1 and not require_type_ext:
        name = parts[0]
        item_type = ext = ""
    else:
        raise InvalidFilename(
            f"Filename does not match file store convention (name.type.ext): {path_str}"
        )
    return dirname, name, item_type, ext


def join_filename(dirname: str | Path, name: str, item_type: str | None, ext: str) -> Path:
    """
    Join a filename into a single path, with optional type and extension.
    """

    parts: list[str] = list(filter(bool, [name, item_type, ext]))  # pyright: ignore
    return Path(dirname) / ".".join(parts)


def parse_file_ext(url_or_path: str | Url | Path) -> FileExt | None:
    """
    Parse a known, canonical file extension from a path, a URL, or even just a
    raw file extension (like "csv" or ".csv").
    """
    front, ext = os.path.splitext(str(url_or_path).split("/")[-1])
    if not ext:
        ext = front
    return FileExt.parse(canonicalize_file_ext(ext))


## Tests


def test_parse_filename():
    import pytest

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

    filename = "missing_type.ext"
    with pytest.raises(InvalidFilename):
        split_filename(filename, require_type_ext=True)


def test_parse_file_ext():
    assert parse_file_ext("test.md") == FileExt.md
    assert parse_file_ext("test.resource.md") == FileExt.md
    assert parse_file_ext(".md") == FileExt.md
    assert parse_file_ext("md") == FileExt.md
    assert parse_file_ext("foobar") is None
    assert parse_file_ext(Url("http://example.com/test.md")) == FileExt.md
    assert parse_file_ext(Url("http://example.com/test")) is None
