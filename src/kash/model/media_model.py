from abc import ABC, abstractmethod
from datetime import date
from enum import Enum
from pathlib import Path

from prettyfmt import abbrev_obj
from pydantic.dataclasses import dataclass

from kash.utils.common.url import Url
from kash.utils.file_utils.file_formats_model import MediaType


class MediaUrlType(Enum):
    """
    Kinds of media URLs and local files.
    """

    audio = "audio"
    """URL or local path for an audio file."""
    video = "video"
    """URL or local path for a video."""

    episode = "episode"
    """URL for a podcast episode."""
    podcast = "podcast"
    """URL for a podcast channel."""
    channel = "channel"
    """URL for a channel."""
    playlist = "playlist"
    """URL for a playlist."""


@dataclass
class HeatmapValue:
    """
    A value in a heatmap. Matches YouTube's format.
    """

    start_time: int
    end_time: int
    value: float


@dataclass
class MediaMetadata:
    """
    Metadata for an audio or video file from a service like YouTube, Vimeo, etc.
    """

    # Fields that match Item fields.
    title: str
    url: Url
    description: str | None = None
    thumbnail_url: Url | None = None

    # The combination of media_id and media_service should be unique.
    media_id: str | None = None
    media_service: str | None = None

    # Extra media fields.
    upload_date: date | None = None
    channel_url: Url | None = None
    view_count: int | None = None
    duration: int | None = None
    heatmap: list[HeatmapValue] | None = None

    def __repr__(self) -> str:
        return abbrev_obj(self)


SERVICE_YOUTUBE = "youtube"
SERVICE_VIMEO = "vimeo"
SERVICE_APPLE_PODCASTS = "apple_podcasts"


class MediaService(ABC):
    """
    An audio or video service like YouTube, Vimeo, Spotify, etc.
    """

    def canonicalize(self, url: Url) -> Url | None:
        """Convert a URL into a canonical form for this service."""
        return self.canonicalize_and_type(url)[0]

    @abstractmethod
    def canonicalize_and_type(self, url: Url) -> tuple[Url | None, MediaUrlType | None]:
        """Convert a URL into a canonical form for this service, including a unique id and URL type."""
        pass

    @abstractmethod
    def get_media_id(self, url: Url) -> str | None:
        """Extract the media ID from a URL. Only for episodes and videos. None for channels etc."""
        pass

    @abstractmethod
    def metadata(self, url: Url) -> MediaMetadata:
        """Return metadata for the media at the given URL."""
        pass

    @abstractmethod
    def thumbnail_url(self, url: Url) -> Url | None:
        """Return a URL that links to the thumbnail of the media."""
        pass

    @abstractmethod
    def timestamp_url(self, url: Url, timestamp: float) -> Url:
        """Return a URL that links to the media at the given timestamp."""
        pass

    @abstractmethod
    def download_media(
        self, url: Url, target_dir: Path, media_types: list[MediaType] | None = None
    ) -> dict[MediaType, Path]:
        """
        Download media from URL and extract to audio or video formats.
        Download all available media types (video, audio, etc.) if media_types
        is not specified.
        """
        pass

    @abstractmethod
    def list_channel_items(self, url: Url) -> list[MediaMetadata]:
        """List all items in a channel."""
        pass
