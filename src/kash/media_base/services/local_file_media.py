import os
import shlex
import subprocess  # Add this import
from pathlib import Path
from urllib.parse import urlparse

from strif import copyfile_atomic
from typing_extensions import override

from kash.config.logger import get_log_file_stream, get_logger
from kash.file_storage.store_filenames import parse_item_filename
from kash.model.media_model import MediaMetadata, MediaService, MediaUrlType
from kash.shell.utils.sys_tool_deps import SysTool, sys_tool_check
from kash.utils.common.format_utils import fmt_loc
from kash.utils.common.url import Url
from kash.utils.errors import FileNotFound, InvalidInput
from kash.utils.file_utils.file_formats_model import FileExt, MediaType

log = get_logger(__name__)


def _run_ffmpeg(cmdline: list[str]) -> None:
    sys_tool_check().require(SysTool.ffmpeg)
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

    def _parse_file_url(self, url: Url) -> Path | None:
        parsed_url = urlparse(url)
        if parsed_url.scheme == "file":
            path = Path(parsed_url.path)
            if not path.exists():
                raise FileNotFound(f"File not found: {path}")
            return path
        else:
            return None

    def get_media_id(self, url: Url) -> str | None:
        path = self._parse_file_url(url)
        if path:
            return path.name
        else:
            return None

    def canonicalize_and_type(self, url: Url) -> tuple[Url | None, MediaUrlType | None]:
        path = self._parse_file_url(url)
        if path:
            _name, _item_type, format, _file_ext = parse_item_filename(path)
            if format and format.is_audio:
                return url, MediaUrlType.audio
            elif format and format.is_video:
                return url, MediaUrlType.video
            else:
                raise InvalidInput(f"Unsupported file format: {format}")
        else:
            return None, None

    def thumbnail_url(self, url: Url) -> Url | None:
        return None

    def timestamp_url(self, url: Url, timestamp: float) -> Url:
        return url

    @override
    def download_media(
        self, url: Url, target_dir: Path, media_types: list[MediaType] | None = None
    ) -> dict[MediaType, Path]:
        path = self._parse_file_url(url)
        if not path:
            raise InvalidInput(f"Not a local file URL: {url}")

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

    def list_channel_items(self, url: Url) -> list[MediaMetadata]:
        raise NotImplementedError()
