from pathlib import Path
from typing import Protocol

from prettyfmt import abbrev_obj
from pydantic.dataclasses import dataclass

from kash.utils.common.url import Url
from kash.utils.file_utils.file_formats_model import FileFormatInfo


@dataclass
class WebPageData:
    """
    Data about a web page, including URL, title and optionally description and
    extracted content.

    The `text` field should be a clean text version of the page, if available.
    The `clean_html` field should be a clean HTML version of the page, if available.
    The `saved_content` is optional but can be used to reference the original content,
    especially for large or non-text content.
    """

    locator: Url | Path
    title: str | None = None
    byline: str | None = None
    description: str | None = None
    text: str | None = None
    clean_html: str | None = None
    saved_content: Path | None = None
    format_info: FileFormatInfo | None = None
    thumbnail_url: Url | None = None

    def __repr__(self):
        return abbrev_obj(self)


class PageExtractor(Protocol):
    def __call__(self, url: Url, raw_html: bytes) -> WebPageData: ...
