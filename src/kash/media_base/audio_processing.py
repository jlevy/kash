from __future__ import annotations

import logging
import subprocess
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


DEFAULT_TRANSCRIPTION_SAMPLE_RATE = 16000
"""Sample rate speech models expect; also the point of downsampling at all."""


def audio_duration(audio_file_path: Path) -> float | None:
    """
    Duration of an audio file in seconds, or None if it cannot be determined.

    Reads only the container metadata, so this costs the same for a five-second clip
    and a twelve-hour recording. Best effort by design: callers use this to size
    budgets, so an unreadable or unusual file should degrade to a default rather than
    fail a run.
    """
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(audio_file_path),
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=True,
        )
        return float(result.stdout.strip())
    except Exception as e:
        log.info("Could not determine audio duration for %s: %s", audio_file_path, e)
        return None


def downsample_to_16khz(
    audio_file_path: Path,
    downsampled_out_path: Path,
    sample_rate: int = DEFAULT_TRANSCRIPTION_SAMPLE_RATE,
) -> tuple[AudioFileStats, AudioFileStats]:
    """
    Downsample audio to mono at `sample_rate`, streaming through ffmpeg.

    Streaming matters for long media: decoding in memory costs roughly 10 MB per
    minute of stereo CD-quality audio, so a twelve-hour recording would need many
    gigabytes of RAM to convert a file that ends up around a hundred megabytes.
    ffmpeg holds only a small window at a time, so cost is flat in duration.
    """
    duration = audio_duration(audio_file_path) or 0.0

    with atomic_output_file(downsampled_out_path) as temp_target:
        subprocess.run(
            [
                "ffmpeg",
                "-nostdin",
                "-y",
                "-loglevel",
                "error",
                "-i",
                str(audio_file_path),
                "-ac",
                "1",
                "-ar",
                str(sample_rate),
                "-f",
                "mp3",
                str(temp_target),
            ],
            check=True,
        )

    before = AudioFileStats(
        duration=duration,
        size=getsize(audio_file_path),
    )
    after = AudioFileStats(
        duration=duration,
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
    total_duration = len(audio) / 1000

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
        duration=total_duration,
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


## Tests


def _require_ffmpeg() -> None:
    """
    Skip when the ffmpeg tools are absent.

    They are an external system dependency that kash checks for at runtime rather than
    installing, so a machine without them should skip these rather than fail.
    """
    import shutil

    import pytest

    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        pytest.skip("ffmpeg and ffprobe are required for audio conversion tests")


def _write_test_tone(path: Path, seconds: float = 1.0) -> None:
    """A small stereo 44.1kHz mp3, so tests do not depend on any fixture file."""
    subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=440:duration={seconds}:sample_rate=44100",
            "-ac",
            "2",
            str(path),
        ],
        check=True,
    )


def test_audio_duration_reads_metadata_without_decoding(tmp_path: Path) -> None:
    _require_ffmpeg()
    tone = tmp_path / "tone.mp3"
    _write_test_tone(tone, seconds=2.0)

    duration = audio_duration(tone)

    assert duration is not None
    assert 1.8 < duration < 2.4  # mp3 framing makes this approximate


def test_audio_duration_degrades_rather_than_raising(tmp_path: Path) -> None:
    not_audio = tmp_path / "not-audio.mp3"
    not_audio.write_bytes(b"this is not audio")

    assert audio_duration(not_audio) is None
    assert audio_duration(tmp_path / "missing.mp3") is None


def test_downsample_produces_mono_at_the_target_rate(tmp_path: Path) -> None:
    _require_ffmpeg()
    tone = tmp_path / "tone.mp3"
    _write_test_tone(tone, seconds=2.0)
    out = tmp_path / "out.mp3"

    before, after = downsample_to_16khz(tone, out)

    assert out.exists()
    assert after.size < before.size
    assert before.duration and 1.8 < before.duration < 2.4

    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=sample_rate,channels",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(out),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    sample_rate, channels = probe.stdout.split()
    assert sample_rate == str(DEFAULT_TRANSCRIPTION_SAMPLE_RATE)
    assert channels == "1"


def test_downsample_honors_a_caller_supplied_rate(tmp_path: Path) -> None:
    _require_ffmpeg()
    tone = tmp_path / "tone.mp3"
    _write_test_tone(tone, seconds=1.0)
    out = tmp_path / "out8k.mp3"

    downsample_to_16khz(tone, out, sample_rate=8000)

    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=sample_rate",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(out),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert probe.stdout.strip() == "8000"
