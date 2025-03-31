import logging
from pathlib import Path

from funlog import log_calls

from kash.media_base.services.local_file_media import LocalFileMedia
from kash.model.media_model import MediaMetadata, MediaService
from kash.utils.common.atomic_var import AtomicVar
from kash.utils.common.url import Url
from kash.utils.errors import InvalidInput
from kash.utils.file_utils.file_formats_model import MediaType

log = logging.getLogger(__name__)


# Start with just local file media.
local_file_media = LocalFileMedia()

_media_services: AtomicVar[list[MediaService]] = AtomicVar([local_file_media])


def get_media_services() -> list[MediaService]:
    return _media_services.copy()


def register_media_service(*services: MediaService) -> None:
    """
    Register more media services.
    """
    new_services = list(s for s in services if s not in _media_services.copy())
    log.info("Registering new media services: %s", new_services)
    _media_services.update(lambda services: services + new_services)


def canonicalize_media_url(url: Url) -> Url | None:
    """
    Return the canonical form of a media URL from a supported service (like YouTube).
    """
    for service in _media_services.copy():
        canonical_url = service.canonicalize(url)
        if canonical_url:
            return canonical_url
    return None


def is_media_url(url: Url) -> bool:
    return canonicalize_media_url(url) is not None


def thumbnail_media_url(url: Url) -> Url | None:
    """
    Return a URL that links to the thumbnail of the media.
    """
    for service in _media_services.copy():
        canonical_url = service.canonicalize(url)
        if canonical_url:
            return service.thumbnail_url(url)
    return None


def timestamp_media_url(url: Url, timestamp: float) -> Url:
    """
    Return a URL that links to the media at the given timestamp.
    """
    for service in _media_services.copy():
        canonical_url = service.canonicalize(url)
        if canonical_url:
            return service.timestamp_url(url, timestamp)
    raise InvalidInput(f"Unrecognized media URL: {url}")


def get_media_id(url: Url | None) -> str | None:
    if not url:
        return None
    for service in _media_services.copy():
        media_id = service.get_media_id(url)
        if media_id:
            return media_id
    return None


@log_calls(level="info")
def get_media_metadata(url: Url) -> MediaMetadata | None:
    """
    Return metadata for the media at the given URL.
    """
    for service in _media_services.copy():
        media_id = service.get_media_id(url)
        if media_id:  # This is an actual video, not a channel etc.
            return service.metadata(url)
    return None


def list_channel_items(url: Url) -> list[MediaMetadata]:
    """
    List all items in a channel.
    """
    for service in _media_services.copy():
        canonical_url = service.canonicalize(url)
        if canonical_url:
            return service.list_channel_items(url)
    raise InvalidInput(f"Unrecognized media URL: {url}")


def download_media_by_service(
    url: Url, target_dir: Path, media_types: list[MediaType] | None = None
) -> dict[MediaType, Path]:
    for service in _media_services.copy():
        canonical_url = service.canonicalize(url)
        if canonical_url:
            return service.download_media(url, target_dir, media_types=media_types)
    raise ValueError(f"Unrecognized media URL: {url}")
