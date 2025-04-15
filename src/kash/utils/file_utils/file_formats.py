import re
import tempfile
from pathlib import Path
from typing import NewType

import regex
from clideps.pkgs.pkg_check import pkg_check

from kash.config.logger import get_logger

log = get_logger(__name__)


def is_full_html_page(content: str) -> bool:
    """
    A full HTML document that is probably best rendered in a browser.
    """
    return bool(re.search(r"<!DOCTYPE html>|<html>|<body>|<head>", content[:2048], re.IGNORECASE))


_yaml_header_pattern = re.compile(r"^---\n\w+:", re.MULTILINE)


def multipart_yaml_count(content: str) -> int:
    """
    Count the apparent number of YAML breaks in the content.
    """
    return len(_yaml_header_pattern.findall(content))


def is_html(content: str) -> bool:
    """
    Check if the content is HTML.
    """
    return bool(
        re.search(
            r"<!DOCTYPE html>|<html>|<body>|<head>|<div>|<p>|<img |<a href", content, re.IGNORECASE
        )
    )


def is_markdown(content: str) -> bool:
    """
    Check if the content is Markdown.
    """
    # First check for plain language with at least 5 words and no special punctuation.
    # This rules out a lot of text-like formats like lockfiles etc.
    sample = content[:2048]
    has_prose = bool(regex.search(r"[\p{L}]+(?:\s+[\p{L}]+){4,}", sample, regex.UNICODE))
    if not has_prose:
        return False

    words = [w for w in regex.split(r"\s+", sample) if w]
    if not words:
        return False

    # Count "natural" words (only letters, no special chars).
    natural_words = [w for w in words if regex.match(r"^[\p{L}]+$", w)]
    # Calculate ratio of natural words to total words
    prose_ratio = len(natural_words) / len(words)
    # Require enough natural words.
    if prose_ratio < 0.4 or len(words) < 5:
        return False

    # Finally check for markdown formatting.
    return len(re.findall(r"^##+ |^- \w|\*\*\w|__\w", content, re.MULTILINE)) >= 2


def read_partial_text(
    path: Path, max_bytes: int = 200 * 1024, encoding: str = "utf-8", errors: str = "strict"
) -> str | None:
    try:
        with path.open("r", encoding=encoding, errors=errors) as file:
            return file.read(max_bytes)
    except UnicodeDecodeError:
        return None


MimeType = NewType("MimeType", str)

MIME_EMPTY = MimeType("inode/x-empty")


def detect_mime_type(filename: str | Path) -> MimeType | None:
    """
    Get the mime type of a file using libmagic heuristics plus more careful
    detection of HTML, Markdown, and multipart YAML.
    """
    pkg_check().require("libmagic")
    import magic

    mime = magic.Magic(mime=True)
    mime_type = mime.from_file(str(filename))
    path = Path(filename)
    if (not mime_type or mime_type == "text/plain") and path.is_file():
        # Also try detecting HTML and Markdown directly to discriminate these from plaintext.
        content = read_partial_text(path)
        if content:
            if multipart_yaml_count(content) >= 2:
                mime_type = "application/yaml"
            elif is_html(content):
                mime_type = "text/html"
            elif is_markdown(content):
                mime_type = "text/markdown"

    return MimeType(mime_type)


def mime_type_is_text(mime_type: MimeType) -> bool:
    """
    Check if the mime type is a text type.
    """
    return (
        mime_type.startswith("text")
        or mime_type.startswith("application/yaml")
        or mime_type.startswith("application/json")
        or mime_type.startswith("application/toml")
        # .js, .jsx, .ts, .tsx are all application/javascript
        or mime_type.startswith("application/javascript")
        or mime_type.startswith("application/xml")
        or mime_type
        in {
            # Shell scripts
            "application/x-sh",
            "application/x-shellscript",
            "application/x-csh",
            # Programming languages
            "application/x-perl",
            "application/x-python",  # Python is "text/x-python" but just in case.
            "application/x-ruby",
            "application/x-php",
            # Document formats
            "application/x-latex",
            "application/x-tex",
            "application/rtf",
        }
    )


## Tests


def test_detect_mime_type():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        empty_file = tmpdir_path / "empty.txt"
        empty_file.touch()

        html_file = tmpdir_path / "example.html"
        with open(html_file, "w") as f:
            f.write("<!DOCTYPE html>\n<html><body><h1>Test</h1></body></html>")

        text_file = tmpdir_path / "example.txt"
        with open(text_file, "w") as f:
            f.write("This is a simple text file with some content.")

        assert detect_mime_type(empty_file) == MIME_EMPTY
        assert detect_mime_type(html_file) == "text/html"
        assert detect_mime_type(text_file) == "text/plain"
