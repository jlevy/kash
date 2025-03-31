import os
from pathlib import Path

from prettyfmt import fmt_lines
from strif import atomic_output_file

from kash.config.logger import get_logger
from kash.media_base.audio_processing import downsample_to_16khz
from kash.media_base.media_services import (
    canonicalize_media_url,
    download_media_by_service,
    get_media_services,
)
from kash.media_base.speech_transcription import deepgram_transcribe_audio
from kash.utils.common.format_utils import fmt_loc
from kash.utils.common.url import Url, as_file_url, is_url
from kash.utils.errors import FileNotFound, InvalidInput, UnexpectedError
from kash.utils.file_utils.file_formats_model import MediaType
from kash.web_content.dir_store import DirStore

log = get_logger(__name__)

# FIXME: Hard-coded dependency for now. Would be better to make it settable.
# transcribe_audio = whisper_transcribe_audio_small
transcribe_audio = deepgram_transcribe_audio


# For simplicity we assume all audio is converted to mp3.
SUFFIX_MP3 = ".full.mp3"
SUFFIX_MP4 = ".full.mp4"
SUFFIX_16KMP3 = ".16k.mp3"
SUFFIX_TRANSCRIPT = ".transcript.txt"


class MediaCache(DirStore):
    """
    Download and cache video, audio, and transcripts. It's important to cache these by
    default as they are time-consuming and costly to download and process. We also
    support local files (as file:// URLs) since we still want to cache downsampled
    extracted audio and transcriptions.
    """

    def __init__(self, root):
        super().__init__(root)

    def _write_transcript(self, url: Url, content: str) -> None:
        transcript_path = self.path_for(url, suffix=SUFFIX_TRANSCRIPT)
        with atomic_output_file(transcript_path) as temp_output:
            with open(temp_output, "w") as f:
                f.write(content)
        log.message("Transcript saved to cache: %s", fmt_loc(transcript_path))

    def _read_transcript(self, url: Url) -> str | None:
        transcript_file = self.find(url, suffix=SUFFIX_TRANSCRIPT)
        if transcript_file:
            log.message("Video transcript already in cache: %s: %s", url, fmt_loc(transcript_file))
            with open(transcript_file) as f:
                return f.read()
        return None

    def _downsample_audio(self, url: Url) -> Path:
        downsampled_audio_file = self.find(url, suffix=SUFFIX_16KMP3)
        if not downsampled_audio_file:
            full_audio_file = self.find(url, suffix=SUFFIX_MP3)
            if not full_audio_file:
                raise ValueError("No audio file found for: %s" % url)
            downsampled_audio_file = self.path_for(url, suffix=SUFFIX_16KMP3)
            log.message(
                "Downsampling audio: %s -> %s",
                fmt_loc(full_audio_file),
                fmt_loc(downsampled_audio_file),
            )
            downsample_to_16khz(full_audio_file, downsampled_audio_file)
        return downsampled_audio_file

    def _do_transcription(self, url: Url, language: str | None = None) -> str:
        """
        Transcribe the audio file (from cache if available) for the given media URL.
        """
        downsampled_audio_file = self._downsample_audio(url)
        log.message(
            "Transcribing audio: %s: %s",
            url,
            fmt_loc(downsampled_audio_file),
        )
        transcript = transcribe_audio(downsampled_audio_file, language=language)
        self._write_transcript(url, transcript)
        return transcript

    def cache(
        self, url: Url, no_cache=False, media_types: list[MediaType] | None = None
    ) -> dict[MediaType, Path]:
        """
        Cache the media files for the given media URL. Returns paths to cached copies
        for each media type (video or audio). Returns cached copies if available,
        unless `no_cache` is True.
        """
        cached_paths: dict[MediaType, Path] = {}

        if not media_types:
            media_types = [MediaType.audio, MediaType.video]

        if not no_cache:
            if MediaType.audio in media_types:
                audio_file = self.find(url, suffix=SUFFIX_MP3)
                if audio_file:
                    log.message("Audio already in cache: %s: %s", url, fmt_loc(audio_file))
                    cached_paths[MediaType.audio] = audio_file
            if MediaType.video in media_types:
                video_file = self.find(url, suffix=SUFFIX_MP4)
                if video_file:
                    log.message("Video already in cache: %s: %s", url, fmt_loc(video_file))
                    cached_paths[MediaType.video] = video_file
            if set(media_types).issubset(cached_paths.keys()):
                return cached_paths
            else:
                log.message(
                    "Downloading to get missing formats. Need %s but have %s.",
                    [t.name for t in media_types],
                    [t.name for t in cached_paths.keys()],
                )

        log.message("Downloading media: %s", url)
        media_paths = download_media_by_service(url, self.root, media_types)
        if MediaType.audio in media_paths:
            audio_path = self.path_for(url, suffix=SUFFIX_MP3)
            os.rename(media_paths[MediaType.audio], audio_path)
            cached_paths[MediaType.audio] = audio_path
        if MediaType.video in media_paths:
            video_path = self.path_for(url, suffix=SUFFIX_MP4)
            os.rename(media_paths[MediaType.video], video_path)
            cached_paths[MediaType.video] = video_path

        log.message(
            "Downloaded media and saved to cache:\n%s",
            fmt_lines([f"{t.name}: {fmt_loc(p)}" for (t, p) in cached_paths.items()]),
        )

        self._downsample_audio(url)

        return cached_paths

    def transcribe(
        self, url_or_path: Url | Path, no_cache=False, language: str | None = None
    ) -> str:
        """
        Transcribe the audio file, caching audio, downsampled audio, and the transcription.
        Return the cached transcript if available, unless `no_cache` is True.
        """
        if not isinstance(url_or_path, Path) and is_url(url_or_path):
            # If it is a URL, cache it locally.
            url = url_or_path
            url = canonicalize_media_url(url)
            if not url:
                log.error("Unrecognized media, current services: %s", get_media_services())
                raise InvalidInput(
                    "Unrecognized media URL (is this media service configured?): %s" % url_or_path
                )
            if not no_cache:
                transcript = self._read_transcript(url)
                if transcript:
                    return transcript
            # Cache all formats since we usually will want them.
            self.cache(url, no_cache)
        elif isinstance(url_or_path, Path):
            # Treat local media files as file:// URLs.
            # Don't need to cache originals but we still will cache audio and transcriptions.
            if not url_or_path.exists():
                raise FileNotFound(f"File not found: {fmt_loc(url_or_path)}")
            url = as_file_url(url_or_path)
        else:
            raise InvalidInput(f"Not a media URL or path: {url_or_path}")

        # Now do the transcription.
        transcript = self._do_transcription(url, language=language)
        if not transcript:
            raise UnexpectedError("No transcript found for: %s" % url)
        return transcript
