from abc import ABC, abstractmethod
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from prettyfmt import abbrev_obj
from pydantic.dataclasses import dataclass

from kash.file_tools.file_formats_model import MediaType
from kash.util.url import Url


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
    description: Optional[str] = None
    thumbnail_url: Optional[Url] = None

    # The combination of media_id and media_service should be unique.
    media_id: Optional[str] = None
    media_service: Optional[str] = None

    # Extra media fields.
    upload_date: Optional[date] = None
    channel_url: Optional[Url] = None
    view_count: Optional[int] = None
    duration: Optional[int] = None
    heatmap: Optional[List[HeatmapValue]] = None

    def __repr__(self) -> str:
        return abbrev_obj(self)


SERVICE_YOUTUBE = "youtube"
SERVICE_VIMEO = "vimeo"
SERVICE_APPLE_PODCASTS = "apple_podcasts"


class MediaService(ABC):
    """
    An audio or video service like YouTube, Vimeo, Spotify, etc.
    """

    def canonicalize(self, url: Url) -> Optional[Url]:
        """Convert a URL into a canonical form for this service."""
        return self.canonicalize_and_type(url)[0]

    @abstractmethod
    def canonicalize_and_type(self, url: Url) -> Tuple[Optional[Url], Optional[MediaUrlType]]:
        """Convert a URL into a canonical form for this service, including a unique id and URL type."""
        pass

    @abstractmethod
    def get_media_id(self, url: Url) -> Optional[str]:
        """Extract the media ID from a URL. Only for episodes and videos. None for channels etc."""
        pass

    @abstractmethod
    def metadata(self, url: Url) -> MediaMetadata:
        """Return metadata for the media at the given URL."""
        pass

    @abstractmethod
    def thumbnail_url(self, url: Url) -> Optional[Url]:
        """Return a URL that links to the thumbnail of the media."""
        pass

    @abstractmethod
    def timestamp_url(self, url: Url, timestamp: float) -> Url:
        """Return a URL that links to the media at the given timestamp."""
        pass

    @abstractmethod
    def download_media(
        self, url: Url, target_dir: Path, media_types: Optional[List[MediaType]] = None
    ) -> Dict[MediaType, Path]:
        """
        Download media from URL and extract to audio or video formats.
        Download all available media types (video, audio, etc.) if media_types
        is not specified.
        """
        pass

    @abstractmethod
    def list_channel_items(self, url: Url) -> List[MediaMetadata]:
        """List all items in a channel."""
        pass
