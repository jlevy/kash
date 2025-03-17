from typing import Protocol

from prettyfmt import abbrev_obj
from pydantic.dataclasses import dataclass

from kash.utils.common.url import Url


@dataclass
class WebPageData:
    """
    Data about a web page, including URL, title and optionally description and extracted content.
    """

    url: Url
    title: str | None = None
    byline: str | None = None
    description: str | None = None
    text: str | None = None
    clean_html: str | None = None
    thumbnail_url: Url | None = None

    def __repr__(self):
        return abbrev_obj(self)


class PageExtractor(Protocol):
    def __call__(self, url: Url, raw_html: bytes) -> WebPageData: ...
