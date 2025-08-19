"""
A simple `Url` type and basic URL handling with no dependencies.
Simply a few convenience types and functions around `urllib`.
"""

import re
from pathlib import Path
from typing import NewType
from urllib.parse import ParseResult, urlparse, urlsplit, urlunsplit

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

HTTP_ONLY = ["http", "https"]
HTTP_OR_FILE = HTTP_ONLY + ["file"]
HTTP_OR_FILE_OR_S3 = HTTP_OR_FILE + ["s3"]


def check_if_url(
    text: UnresolvedLocator, only_schemes: list[str] | None = None
) -> ParseResult | None:
    """
    Convenience function to check if a string or Path is a URL and if so return
    the `urlparse.ParseResult`.

    Also returns false for Paths, so that it's easy to use local paths and URLs
    (`Locator`s) interchangeably. Can provide `HTTP_ONLY` or `HTTP_OR_FILE`
    or `HTTP_OR_FILE_OR_S3` to restrict to only certain schemes.
    restrict to only certain schemes.
    """
    if isinstance(text, Path):
        return None
    text = str(text)  # Handle paths or anything else unexpected.
    try:
        result = urlparse(text)
        if only_schemes:
            return result if result.scheme in only_schemes else None
        else:
            # Consider it a URL if the scheme is present and longer than a single character.
            # This helps avoid misinterpreting Windows drive letters (e.g., "C:\foo") as schemes.
            return result if result.scheme and len(result.scheme) > 1 else None
    except ValueError:
        return None


def is_url(text: UnresolvedLocator, only_schemes: list[str] | None = None) -> bool:
    """
    Check if a string is a URL. For convenience, also returns false for
    Paths, so that it's easy to use local paths and URLs interchangeably.
    """
    return check_if_url(text, only_schemes) is not None


def is_file_url(url: str | Url) -> bool:
    """
    Is URL a file:// URL? Does not check for local file paths.
    """
    return url.startswith("file://")


def is_s3_url(url: str | Url) -> bool:
    """
    Is URL an S3 URL?
    """
    return url.startswith("s3://")


def parse_http_url(url: str | Url) -> ParseResult:
    """
    Parse an http/https URL and return the parsed result, raising ValueError if
    not an http/https URL.
    """
    parsed_url = urlparse(url)
    if parsed_url.scheme in ("http", "https"):
        return parsed_url
    else:
        raise ValueError(f"Not an http/https URL: {url}")


def parse_file_url(url: str | Url) -> Path:
    """
    Parse a file URL and return the path, raising ValueError if not a file URL.
    """
    parsed_url = urlparse(url)
    if parsed_url.scheme == "file":
        return Path(parsed_url.path)
    else:
        raise ValueError(f"Not a file URL: {url}")


def parse_s3_url(url: str | Url) -> tuple[str, str]:
    """
    Parse an S3 URL and return the bucket and key, raising ValueError if not an
    S3 URL.
    """
    parsed_url = urlparse(url)
    if parsed_url.scheme == "s3":
        return parsed_url.netloc, parsed_url.path.lstrip("/")
    else:
        raise ValueError(f"Not an S3 URL: {url}")


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
    url: Url,
    check_schemes: list[str] | None = HTTP_OR_FILE_OR_S3,
    drop_fragment: bool = True,
    resolve_local_paths: bool = True,
) -> Url:
    """
    Minimal URL normalization. By default also enforces http/https/file URLs and
    removes fragment. By default enforces http/https/file URLs but this can be
    adjusted with `check_schemes`.
    """

    fragment: str | None
    scheme, netloc, path, query, fragment = urlsplit(url)

    # urlsplit is too forgiving.
    if check_schemes and scheme not in check_schemes:
        raise ValueError(f"Scheme {scheme!r} not in allowed schemes: {check_schemes!r}: {url}")

    if drop_fragment:
        fragment = None
    if path == "/":
        path = ""
    if scheme == "file" and path and resolve_local_paths:
        path = str(Path(path).resolve())

    normalized_url = urlunsplit((scheme, netloc, path, query, fragment))

    return Url(normalized_url)


def is_valid_path(text: UnresolvedLocator) -> bool:
    """
    Sanity check if the input is plausibly a file path, i.e. not a URL or malformed in
    an obvious way. Does not check for existence or OS-specific naming restrictions.
    For a more thorough check there are other more complex options like:
    https://github.com/thombashi/pathvalidate
    """
    if isinstance(text, Path):
        return True
    elif isinstance(text, str):
        path_str = text
    else:
        return False

    # Check for empty or whitespace-only strings or null characters
    # (never acceptable paths).
    if not path_str or path_str.isspace():
        return False
    if "\0" in path_str:
        return False

    # Explicitly disallow URLs.
    if is_url(path_str):
        return False

    # As a final lightweight check, ensure it can be instantiated as a Path object
    # This doesn't validate existence or character restrictions.
    try:
        _ = Path(path_str)
    except (TypeError, ValueError):
        return False

    return True


## Tests


def test_is_url():
    assert is_url("http://") == True
    assert is_url("http://example.com") == True
    assert is_url("https://example.com") == True
    assert is_url("ftp://example.com") == True
    assert is_url("file:///path/to/file") == True
    assert is_url("file://hostname/path/to/file") == True
    assert is_url("http://example.com", only_schemes=HTTP_ONLY) == True
    assert is_url("https://example.com", only_schemes=HTTP_ONLY) == True

    assert is_url("invalid-url") == False
    assert is_url("www.example.com") == False
    assert is_url("ftp://example.com", only_schemes=HTTP_ONLY) == False
    assert is_url("file:///path/to/file", only_schemes=HTTP_ONLY) == False

    assert is_url("www.example.com") is False
    assert is_url("c:\\path\\to\\file") is False
    assert is_url("/foo/bar") is False
    assert is_url("//foo") is False


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
        normalize_url(url=Url("/not/a/URL"))
        raise AssertionError()
    except ValueError as e:
        assert str(e) == "Scheme '' not in allowed schemes: ['http', 'https', 'file']: /not/a/URL"

    try:
        normalize_url(Url("ftp://example.com"))
        raise AssertionError()
    except ValueError as e:
        assert (
            str(e)
            == "Scheme 'ftp' not in allowed schemes: ['http', 'https', 'file']: ftp://example.com"
        )


def test_is_path():
    assert is_valid_path("foo/bar") is True
    assert is_valid_path("/foo/bar") is True
    assert is_valid_path("./foo/bar") is True
    assert is_valid_path("../foo/bar") is True
    assert is_valid_path("foo.txt") is True
    assert is_valid_path(Path("foo/bar")) is True
    assert is_valid_path(Path()) is True
    assert is_valid_path(".") is True
    assert is_valid_path("..") is True
    assert is_valid_path("C:\\Users\\name") is True  # Windows-style
    assert is_valid_path("file_with:colon.txt") is True  # Valid on POSIX
    assert is_valid_path(Url("relative/path")) is True  # Url type with relative content

    assert is_valid_path("http://example.com") is False
    assert is_valid_path("https://example.com/path") is False
    assert is_valid_path("file:///path/to/file") is False
    assert is_valid_path(Url("http://example.com")) is False
    assert is_valid_path("") is False
    assert is_valid_path("  ") is False
    assert is_valid_path("foo\0bar.txt") is False
    assert is_valid_path(None) is False  # pyright: ignore
    assert is_valid_path(123) is False  # pyright: ignore

    # Edge cases
    assert is_valid_path("www.example.com") is True  # No scheme
    assert str(Path("")) == "."
    assert str(Path(" ")) == " "
    assert is_valid_path(Path(" ")) is True  # A bad idea but allowed
    assert is_valid_path(Path("")) is True
    assert is_valid_path(" ") is False
    assert is_valid_path("") is False
