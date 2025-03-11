from typing import Optional, Protocol

from prettyfmt import abbrev_obj

from pydantic.dataclasses import dataclass

from kash.util.url import Url


@dataclass
class WebPageData:
    """
    Data about a web page, including URL, title and optionally description and extracted content.
    """

    url: Url
    title: Optional[str] = None
    byline: Optional[str] = None
    description: Optional[str] = None
    text: Optional[str] = None
    clean_html: Optional[str] = None
    thumbnail_url: Optional[Url] = None

    def __repr__(self):
        return abbrev_obj(self)


class PageExtractor(Protocol):
    def __call__(self, url: Url, raw_html: bytes) -> WebPageData: ...
