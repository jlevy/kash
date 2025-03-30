import logging
from pathlib import Path

from prettyfmt import fmt_path

from kash.config.settings import atomic_global_settings, global_settings
from kash.media_base.media_cache import MediaCache
from kash.utils.common.url import Url
from kash.utils.file_utils.file_formats_model import MediaType

log = logging.getLogger(__name__)

_media_cache = MediaCache(global_settings().media_cache_dir)


def reset_media_cache_dir(path: Path):
    """
    Reset the current media cache directory, if it has changed.
    """
    with atomic_global_settings().updates() as settings:
        current_cache_dir = settings.media_cache_dir

        if current_cache_dir != path:
            settings.media_cache_dir = path
            global _media_cache
            _media_cache = MediaCache(path)
            log.info("Using media cache: %s", fmt_path(path))


def cache_and_transcribe(
    url_or_path: Url | Path, no_cache=False, language: str | None = None
) -> str:
    """
    Download and transcribe audio or video, saving in cache. If no_cache is
    True, force fresh download.
    """
    return _media_cache.transcribe(url_or_path, no_cache=no_cache, language=language)


def cache_media(
    url: Url, no_cache=False, media_types: list[MediaType] | None = None
) -> dict[MediaType, Path]:
    """
    Download audio and video (if available), saving in cache. If no_cache is
    True, force fresh download.
    """
    return _media_cache.cache(url, no_cache, media_types)
