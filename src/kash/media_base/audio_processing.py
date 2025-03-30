import logging
from os.path import getsize
from pathlib import Path

from strif import atomic_output_file

log = logging.getLogger(__name__)


def downsample_to_16khz(audio_file_path: Path, downsampled_out_path: Path) -> None:
    from pydub import AudioSegment

    audio = AudioSegment.from_mp3(audio_file_path)
    audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)

    with atomic_output_file(downsampled_out_path) as temp_target:
        audio.export(temp_target, format="mp3")

    log.info(
        "Downsampled %s -> %s: size %s to 16kHz size %s (%sX reduction)",
        audio_file_path,
        downsampled_out_path,
        getsize(audio_file_path),
        getsize(downsampled_out_path),
        getsize(audio_file_path) / getsize(downsampled_out_path),
    )
