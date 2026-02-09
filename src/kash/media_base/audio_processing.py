from __future__ import annotations

import logging
from dataclasses import dataclass
from os.path import getsize
from pathlib import Path

from prettyfmt import fmt_path, fmt_size_human
from strif import atomic_output_file

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class AudioFileStats:
    duration: float
    size: int

    def __str__(self) -> str:
        return f"duration {self.duration:.2f}s, size {fmt_size_human(self.size)}"


def downsample_to_16khz(
    audio_file_path: Path, downsampled_out_path: Path
) -> tuple[AudioFileStats, AudioFileStats]:
    from pydub import AudioSegment

    audio = AudioSegment.from_mp3(audio_file_path)
    audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)

    with atomic_output_file(downsampled_out_path) as temp_target:
        audio.export(temp_target, format="mp3")

    before = AudioFileStats(
        duration=len(audio) / 1000,
        size=getsize(audio_file_path),
    )
    after = AudioFileStats(
        duration=len(audio) / 1000,
        size=getsize(downsampled_out_path),
    )
    log.info(
        "Downsampled %s -> %s: %s to 16kHz %s (%sX reduction)",
        fmt_path(audio_file_path),
        fmt_path(downsampled_out_path),
        before,
        after,
        before.size / after.size,
    )

    return before, after


# TODO: Test and integrate with JSON caching of transcription results.
def slice_audio_segments(
    audio_file_path: Path, segments: list[tuple[float, float]], output_path: Path
) -> tuple[AudioFileStats, AudioFileStats]:
    """
    Takes a list of time segments in seconds and creates a new audio file
    containing only those segments concatenated together.
    """
    from pydub import AudioSegment

    # Load the audio file.
    audio = AudioSegment.from_file(audio_file_path)
    audio_duration = len(audio) / 1000

    # Extract and concatenate each segment.
    result: AudioSegment = AudioSegment.empty()
    slices_duration = 0
    for start_sec, end_sec in segments:
        # Convert seconds to milliseconds for pydub.
        start_ms = int(start_sec * 1000)
        end_ms = int(end_sec * 1000)

        # Extract the segment and add to result.
        segment_audio = audio[start_ms:end_ms]
        result += segment_audio
        slices_duration += end_sec - start_sec

    # Export the concatenated audio.
    with atomic_output_file(output_path) as temp_target:
        result.export(temp_target, format="mp3")

    before = AudioFileStats(
        duration=audio_duration,
        size=getsize(audio_file_path),
    )
    after = AudioFileStats(
        duration=slices_duration,
        size=getsize(output_path),
    )
    log.info(
        "Sliced audio: %s -> %s: extracted %d segments, %s to %s",
        fmt_path(audio_file_path),
        fmt_path(output_path),
        len(segments),
        before,
        after,
    )

    return before, after
