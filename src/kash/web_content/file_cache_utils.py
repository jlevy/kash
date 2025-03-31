from pathlib import Path

from prettyfmt import fmt_lines, fmt_path

from kash.config.logger import get_logger
from kash.config.settings import atomic_global_settings, global_settings
from kash.model.items_model import Item
from kash.model.media_model import MediaType
from kash.utils.common.url import Url
from kash.utils.errors import FileNotFound, InvalidInput
from kash.utils.file_utils.file_formats_model import detect_media_type
from kash.web_content.canon_url import canonicalize_url
from kash.web_content.local_file_cache import Loadable, LocalFileCache

log = get_logger(__name__)


# Simple global cache for misc use. No expiration.
_global_content_cache = LocalFileCache(global_settings().content_cache_dir)

_content_cache = _global_content_cache


def reset_content_cache_dir(path: Path):
    """
    Reset the current content cache directory, if it has changed.
    """
    with atomic_global_settings().updates() as settings:
        current_cache_dir = settings.content_cache_dir

        if current_cache_dir != path:
            settings.content_cache_dir = path
            global _content_cache
            _content_cache = LocalFileCache(global_settings().content_cache_dir)
            log.info("Using web cache: %s", fmt_path(path))


def cache_file(source: Url | Path | Loadable, global_cache: bool = False) -> tuple[Path, bool]:
    """
    Return a local cached copy of the item. If it is an URL, content is fetched.
    Raises requests.HTTPError if the URL is not reachable. If it is a Path or
    a Loadable, a cached copy is returned.
    """
    cache = _global_content_cache if global_cache else _content_cache
    path, was_cached = cache.cache(source)
    return path, was_cached


def cache_resource(item: Item) -> dict[MediaType, Path]:
    """
    Cache a resource item for an external local path or a URL, fetching or
    copying as needed. For media this may yield more than one format.
    """
    from kash.exec.preconditions import is_resource
    from kash.media_base.media_services import is_media_url
    from kash.media_base.media_tools import cache_media

    if not is_resource(item):
        raise ValueError(f"Item is not a resource: {item}")

    path = None
    result: dict[MediaType, Path] = {}
    if item.url:
        if is_media_url(item.url):
            result = cache_media(item.url)
        else:
            path, _was_cached = cache_file(item.url)
    elif item.external_path:
        path = Path(item.external_path)
        if not path.is_file():
            raise FileNotFound(f"External path not found: {path}")
        path, _was_cached = cache_file(path)
    elif item.original_filename:
        path = Path(item.original_filename)
        if not path.is_file():
            raise FileNotFound(f"Original filename not found: {path}")
        path, _was_cached = cache_file(path)
    else:
        raise ValueError(f"Item has no URL or external path: {item}")

    # If we just have the local file path, determine its format.
    if not result and path:
        result = {detect_media_type(path): path}

    log.message(
        "Cached resource %s:\n%s",
        item.as_str_brief(),
        fmt_lines(
            f"{media_type.value}: {fmt_path(media_path)}"
            for media_type, media_path in result.items()
        ),
    )

    return result


def get_url_html(item: Item) -> tuple[Url, str]:
    """
    Returns the HTML content of an URL item, using the content cache,
    or the body of the item if it has a URL and HTML body.
    """
    from kash.exec.preconditions import has_html_body, is_url_item

    if not item.url:
        raise InvalidInput("Item must have a URL or an HTML body")
    url = Url(canonicalize_url(item.url))

    if is_url_item(item):
        path, _was_cached = cache_file(url)
        with open(path) as file:
            html_content = file.read()
    else:
        if not item.body or not has_html_body(item):
            raise InvalidInput("Item must have a URL or an HTML body")
        html_content = item.body

    return url, html_content
