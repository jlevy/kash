"""
A simple `Url` type and basic URL handling with no dependencies.
"""

import re
from pathlib import Path
from typing import NewType
from urllib.parse import urlparse, urlsplit, urlunsplit

Url = NewType("Url", str)
"""
A minimalist URL type that can be used in place of a string but allows
for better clarity and type checking.
"""

Locator = Url | Path
"""
A useful type to reference a path or URL.
"""

UnresolvedLocator = str | Locator
"""
A string that may not be resolved to a URL or path.
"""


def is_url(text: UnresolvedLocator, http_only: bool = False) -> bool:
    """
    Check if a string is a URL. For convenience, also returns false for
    Paths, so that it's easy to use local paths and URLs interchangeably.
    """
    if isinstance(text, Path):
        return False
    text = str(text)  # Handle paths or anything else unexpected.
    try:
        result = urlparse(text)
        if http_only:
            return result.scheme in ["http", "https"]
        else:
            return result.scheme != ""
    except ValueError:
        return False


def is_file_url(url: str | Url) -> bool:
    """
    Is URL a file:// URL?
    """
    return url.startswith("file://")


def parse_file_url(url: str | Url) -> Path | None:
    """
    Parse a file URL and return the path, or None if not a file URL.
    """
    parsed_url = urlparse(url)
    if parsed_url.scheme == "file":
        return Path(parsed_url.path)
    else:
        return None


def as_file_url(path: str | Path) -> Url:
    """
    Resolve a path as a file:// URL. Resolves relative paths to absolute paths on
    the local filesystem.
    """
    if is_file_url(str(path)):
        return Url(str(path))
    else:
        abs_path = Path(path).resolve()
        return Url(f"file://{abs_path}")


def normalize_url(
    url: Url, http_or_file_only=True, drop_fragment=True, resolve_local_paths=True
) -> Url:
    """
    Minimal URL normalization. By default also enforces http/https/file URLs and
    removes fragment.
    """
    # urlsplit is too forgiving.
    if (
        http_or_file_only
        and not url.startswith("http://")
        and not url.startswith("https://")
        and not is_file_url(url)
    ):
        raise ValueError(f"Expected http:// or https:// or file:// URL but found: {url}")

    fragment: str | None
    scheme, netloc, path, query, fragment = urlsplit(url)

    if drop_fragment:
        fragment = None
    if path == "/":
        path = ""
    if scheme == "file" and path and resolve_local_paths:
        path = str(Path(path).resolve())

    normalized_url = urlunsplit((scheme, netloc, path, query, fragment))

    return Url(normalized_url)


## Tests


def test_is_url():
    assert is_url("http://") == True
    assert is_url("http://example.com") == True
    assert is_url("https://example.com") == True
    assert is_url("ftp://example.com") == True
    assert is_url("file:///path/to/file") == True
    assert is_url("file://hostname/path/to/file") == True
    assert is_url("invalid-url") == False
    assert is_url("www.example.com") == False
    assert is_url("http://example.com", http_only=True) == True
    assert is_url("https://example.com", http_only=True) == True
    assert is_url("ftp://example.com", http_only=True) == False
    assert is_url("file:///path/to/file", http_only=True) == False


def test_as_file_url():
    assert as_file_url("file:///path/to/file") == "file:///path/to/file"
    assert as_file_url("/path/to/file") == "file:///path/to/file"
    assert re.match(r"file:///.*/path/to/file", as_file_url("path/to/file"))


def test_normalize_url():
    assert normalize_url(Url("http://example.com")) == "http://example.com"
    assert normalize_url(Url("http://www.example.com/")) == "http://www.example.com"
    assert normalize_url(Url("https://example.com")) == "https://example.com"
    assert (
        normalize_url(Url("https://example.com/foo/bar.html#fragment"), drop_fragment=True)
        == "https://example.com/foo/bar.html"
    )
    assert (
        normalize_url(Url("https://example.com#fragment"), drop_fragment=False)
        == "https://example.com#fragment"
    )
    assert normalize_url(Url("file:///path/to/file/")) == "file:///path/to/file"
    assert (
        normalize_url(Url("file:///path/to/file#fragment"), drop_fragment=True)
        == "file:///path/to/file"
    )
    assert (
        normalize_url(Url("file:///path/to/file#fragment"), drop_fragment=False)
        == "file:///path/to/file#fragment"
    )
    try:
        normalize_url(Url("ftp://example.com"))
        raise AssertionError()
    except ValueError as e:
        assert str(e) == "Expected http:// or https:// or file:// URL but found: ftp://example.com"
