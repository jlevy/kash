from __future__ import annotations

import os
import shlex
import subprocess  # Add this import
from pathlib import Path
from urllib.parse import urlparse

from clideps.pkgs.pkg_check import pkg_check
from strif import copyfile_atomic
from typing_extensions import override

from kash.config.logger import get_log_file_stream, get_logger
from kash.file_storage.store_filenames import parse_item_filename
from kash.model.media_model import MediaMetadata, MediaService, MediaUrlType
from kash.utils.common.format_utils import fmt_loc
from kash.utils.common.url import Url
from kash.utils.common.url_slice import Slice
from kash.utils.errors import FileNotFound, InvalidInput
from kash.utils.file_utils.file_formats_model import FileExt, MediaType

log = get_logger(__name__)


def _run_ffmpeg(cmdline: list[str]) -> None:
    pkg_check().require("ffmpeg")
    log.message("Running: %s", " ".join([shlex.quote(arg) for arg in cmdline]))
    subprocess.run(
        cmdline,
        check=True,
        stdout=get_log_file_stream(),
        stderr=get_log_file_stream(),
    )


class LocalFileMedia(MediaService):
    """
    Handle local media files as file:// URLs.
    """

    def _parse_file_url(self, url: Url, *, must_exist: bool = True) -> Path | None:
        parsed_url = urlparse(url)
        if parsed_url.scheme == "file":
            path = Path(parsed_url.path)
            if must_exist and not path.exists():
                raise FileNotFound(f"File not found: {path}")
            return path
        else:
            return None

    @override
    def get_media_id(self, url: Url) -> str | None:
        path = self._parse_file_url(url, must_exist=False)
        if path:
            return path.name
        else:
            return None

    @override
    def canonicalize_and_type(self, url: Url) -> tuple[Url | None, MediaUrlType | None]:
        # Existence is not required: item identity uses canonicalize on stored
        # file:// URLs, and those sources (temp recordings, etc.) often vanish.
        path = self._parse_file_url(url, must_exist=False)
        if path:
            _name, _item_type, format, _file_ext = parse_item_filename(path)
            if format and format.is_audio:
                return url, MediaUrlType.audio
            elif format and format.is_video:
                return url, MediaUrlType.video
            else:
                return None, None
        else:
            return None, None

    @override
    def thumbnail_url(self, url: Url) -> Url | None:
        return None

    @override
    def timestamp_url(self, url: Url, timestamp: float) -> Url:
        return url

    @override
    def download_media(
        self,
        url: Url,
        target_dir: Path,
        *,
        media_types: list[MediaType] | None = None,
        slice: Slice | None = None,
    ) -> dict[MediaType, Path]:
        path = self._parse_file_url(url)
        if not path:
            raise InvalidInput(f"Not a local file URL: {url}")
        if slice:
            raise NotImplementedError("Slicing currently not supported for local files")

        _name, _item_type, format, file_ext = parse_item_filename(path)
        os.makedirs(target_dir, exist_ok=True)

        if format and format.is_audio:
            target_path = target_dir / (path.stem + ".mp3")
            if file_ext == FileExt.mp3:
                log.message(
                    "Copying local audio file: %s -> %s", fmt_loc(path), fmt_loc(target_dir)
                )
                # If the file is already an MP3 so just copy it.
                copyfile_atomic(path, target_path)
            else:
                log.message(
                    "Converting local audio file: %s -> %s", fmt_loc(path), fmt_loc(target_dir)
                )

                _run_ffmpeg(["ffmpeg", "-i", str(path), "-f", "mp3", str(target_path)])
            return {MediaType.audio: target_path}
        elif format and format.is_video:
            video_target_path = target_dir / (path.stem + ".mp4")
            audio_target_path = target_dir / (path.stem + ".mp3")

            log.message(
                "Converting local video file: %s -> %s",
                fmt_loc(path),
                fmt_loc(video_target_path),
            )
            _run_ffmpeg(
                [
                    "ffmpeg",
                    "-i",
                    str(path),
                    "-c:v",
                    "libx264",
                    "-c:a",
                    "aac",
                    "-f",
                    "mp4",
                    str(video_target_path),
                ]
            )

            log.message(
                "Extracting audio from video file: %s -> %s",
                fmt_loc(path),
                fmt_loc(audio_target_path),
            )
            _run_ffmpeg(
                [
                    "ffmpeg",
                    "-i",
                    str(path),
                    "-q:a",
                    "0",
                    "-map",
                    "a",
                    "-f",
                    "mp3",
                    str(audio_target_path),
                ]
            )

            return {
                MediaType.video: video_target_path,
                MediaType.audio: audio_target_path,
            }
        else:
            raise InvalidInput(f"Unsupported file format: {format}")

    @override
    def metadata(self, url: Url, full: bool = False) -> MediaMetadata:
        path = self._parse_file_url(url)
        if not path:
            raise InvalidInput(f"Not a local file URL: {url}")

        name, _item_type, _format, _file_ext = parse_item_filename(path)
        return MediaMetadata(
            title=name,
            url=url,
            media_id=None,
            media_service=None,
        )

    @override
    def list_channel_items(self, url: Url) -> list[MediaMetadata]:
        raise NotImplementedError()


## Tests


def test_canonicalize_missing_local_media_file():
    """file:// identity must not require the source file to still exist."""
    from kash.utils.common.url import Url

    missing = Url("file:///tmp/does-not-exist-kash-recording.mp4")
    service = LocalFileMedia()

    canonical, media_type = service.canonicalize_and_type(missing)
    assert canonical == missing
    assert media_type == MediaUrlType.video
    assert service.get_media_id(missing) == "does-not-exist-kash-recording.mp4"
    assert service.canonicalize(missing) == missing


def test_canonicalize_non_media_file_url():
    service = LocalFileMedia()
    text_url = Url("file:///tmp/notes.txt")
    assert service.canonicalize_and_type(text_url) == (None, None)


def test_parse_file_url_requires_existence_for_download():
    from kash.utils.common.url import Url

    missing = Url("file:///tmp/does-not-exist-kash-recording.mp4")
    service = LocalFileMedia()
    try:
        service._parse_file_url(missing)
    except FileNotFound:
        return
    raise AssertionError("expected FileNotFound when the local media file is gone")
