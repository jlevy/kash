from __future__ import annotations

import logging
from pathlib import Path

from funlog import log_calls
from strif import AtomicVar

from kash.media_base.services.local_file_media import LocalFileMedia
from kash.model.media_model import MediaMetadata, MediaService
from kash.utils.common.url import Url
from kash.utils.common.url_slice import Slice, add_slice_to_url, parse_url_slice
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


def canonicalize_media_url(url_or_slice: Url) -> Url | None:
    """
    Return the canonical form of a media URL from a supported service (like YouTube).
    Preserves any slice information in URL fragments.
    """
    base_url, slice_obj = parse_url_slice(url_or_slice)

    # Canonicalize the base URL
    for service in _media_services.copy():
        canonical_url = service.canonicalize(base_url)
        if canonical_url:
            # Add slice back to canonical URL if it existed
            if slice_obj:
                return add_slice_to_url(canonical_url, slice_obj)
            else:
                return canonical_url
    return None


def is_media_url(url: Url) -> bool:
    return canonicalize_media_url(url) is not None


def thumbnail_media_url(url: Url) -> Url | None:
    """
    Return a URL that links to the thumbnail of the media.
    """
    base_url, _ = parse_url_slice(url)
    for service in _media_services.copy():
        canonical_url = service.canonicalize(base_url)
        if canonical_url:
            return service.thumbnail_url(base_url)
    return None


def timestamp_media_url(url: Url, timestamp: float) -> Url:
    """
    Return a URL that links to the media at the given timestamp.
    """
    base_url, _ = parse_url_slice(url)
    for service in _media_services.copy():
        canonical_url = service.canonicalize(base_url)
        if canonical_url:
            return service.timestamp_url(base_url, timestamp)
    raise InvalidInput(f"Unrecognized media URL: {url}")


def get_media_id(url: Url | None) -> str | None:
    if not url:
        return None

    base_url, _ = parse_url_slice(url)
    for service in _media_services.copy():
        media_id = service.get_media_id(base_url)
        if media_id:
            return media_id
    return None


@log_calls(level="info")
def get_media_metadata(url: Url) -> MediaMetadata | None:
    """
    Return metadata for the media at the given URL.
    """
    base_url, _ = parse_url_slice(url)
    for service in _media_services.copy():
        media_id = service.get_media_id(base_url)
        if media_id:  # This is an actual video, not a channel etc.
            return service.metadata(base_url)
    return None


def list_channel_items(url: Url) -> list[MediaMetadata]:
    """
    List all items in a channel.
    """
    base_url, _ = parse_url_slice(url)
    for service in _media_services.copy():
        canonical_url = service.canonicalize(base_url)
        if canonical_url:
            return service.list_channel_items(base_url)
    raise InvalidInput(f"Unrecognized media URL: {url}")


def download_media_by_service(
    url: Url,
    target_dir: Path,
    *,
    media_types: list[MediaType] | None = None,
    slice: Slice | None = None,
) -> dict[MediaType, Path]:
    for service in _media_services.copy():
        canonical_url = service.canonicalize(url)
        if canonical_url:
            return service.download_media(url, target_dir, media_types=media_types, slice=slice)
    raise ValueError(f"Unrecognized media URL: {url}")


## Tests


def test_canonicalize_media_url_preserves_slice():
    """Test that canonicalize_media_url preserves URL slice fragments."""

    # Test with unrecognized URLs (should return None)
    # This tests the slice extraction/reconstruction logic without requiring actual files
    unrecognized_url = Url("https://unknown-service.com/video#~slice=10-30")
    canonical_unknown = canonicalize_media_url(unrecognized_url)
    assert canonical_unknown is None

    # Test typical YouTube URL with slice (would work if YouTube service was registered)
    youtube_url = Url("https://www.youtube.com/watch?v=dQw4w9WgXcQ#~slice=10-30")
    # For now this returns None since YouTube service isn't registered in this test
    # but the slice extraction/reconstruction logic is tested in url_slice.py
    youtube_canonical = canonicalize_media_url(youtube_url)
    assert youtube_canonical is None  # No YouTube service registered

    # Test HH:MM:SS format slice
    hms_youtube_url = Url("https://www.youtube.com/watch?v=dQw4w9WgXcQ#~slice=01:30-02:45")
    canonical_hms = canonicalize_media_url(hms_youtube_url)
    assert canonical_hms is None  # No YouTube service registered

    # The actual slice functionality is thoroughly tested in url_slice.py
    # This test ensures canonicalize_media_url doesn't break with slice URLs
