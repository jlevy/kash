from funlog import log_if_modifies

from kash.media_base.media_services import canonicalize_media_url, thumbnail_media_url
from kash.util.url import Url, normalize_url

_normalize_url = log_if_modifies(level="info")(normalize_url)


def canonicalize_url(url: Url) -> Url:
    """
    Canonicalize a URL for known services, otherwise do basic normalization on the URL.
    """
    return canonicalize_media_url(url) or _normalize_url(url)


def thumbnail_url(url: Url) -> Url | None:
    """
    Return a URL for a thumbnail of the given URL, if available.
    """
    # Currently just for videos. Consider adding support for images and webpages.
    return thumbnail_media_url(url)
