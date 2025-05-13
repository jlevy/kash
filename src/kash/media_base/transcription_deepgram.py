from __future__ import annotations

from os.path import getsize
from pathlib import Path
from typing import TYPE_CHECKING

from clideps.env_vars.dotenv_utils import load_dotenv_paths
from httpx import Timeout

from kash.config.logger import CustomLogger, get_logger
from kash.config.settings import global_settings
from kash.media_base.transcription_format import SpeakerSegment, format_speaker_segments
from kash.utils.errors import ApiError, ContentError

if TYPE_CHECKING:
    from deepgram import PrerecordedResponse

log: CustomLogger = get_logger(__name__)


def deepgram_transcribe_raw(
    audio_file_path: Path, language: str | None = None
) -> PrerecordedResponse:
    """
    Transcribe an audio file using Deepgram and return the raw response.
    """
    # Slow import, do lazily.
    from deepgram import (
        ClientOptionsFromEnv,
        DeepgramClient,
        FileSource,
        ListenRESTClient,
        PrerecordedOptions,
        PrerecordedResponse,
    )

    size = getsize(audio_file_path)
    log.info(
        "Transcribing via Deepgram (language %r): %s (size %s)", language, audio_file_path, size
    )

    load_dotenv_paths(True, True, global_settings().system_config_dir)
    deepgram = DeepgramClient("", ClientOptionsFromEnv())

    with open(audio_file_path, "rb") as audio_file:
        buffer_data = audio_file.read()

    payload: FileSource = {
        "buffer": buffer_data,
    }

    options = PrerecordedOptions(model="nova-2", smart_format=True, diarize=True, language=language)
    client: ListenRESTClient = deepgram.listen.rest.v("1")  # pyright: ignore

    response = client.transcribe_file(payload, options, timeout=Timeout(500))
    if not isinstance(response, PrerecordedResponse):
        raise ApiError("Deepgram returned an unexpected response type")

    return response


def deepgram_transcribe_audio(audio_file_path: Path, language: str | None = None) -> str:
    response = deepgram_transcribe_raw(audio_file_path, language)

    log.save_object("Deepgram response", None, response)

    diarized_segments = _deepgram_diarized_segments(response)
    log.debug("Diarized response: %s", diarized_segments)

    if not diarized_segments:
        raise ContentError(
            f"No speaker segments found in Deepgram response (are voices silent or missing?): {audio_file_path}"
        )

    formatted_segments = format_speaker_segments(diarized_segments)  # noqa: F821

    return formatted_segments


def _deepgram_diarized_segments(data, confidence_threshold=0.3) -> list[SpeakerSegment]:
    """
    Process Deepgram diarized results into text segments per speaker.
    """

    speaker_segments: list[SpeakerSegment] = []
    current_speaker = 0
    current_text: list[tuple[float, str]] = []
    current_confidences: list[float] = []
    segment_start = 0.0
    segment_end = 0.0

    word_info_list = data["results"]["channels"][0]["alternatives"][0]["words"]

    for word_info in word_info_list:
        word_confidence = word_info["confidence"]
        word_speaker = word_info["speaker"]
        word_start = float(word_info["start"])
        word_end = float(word_info["end"])
        punctuated_word = word_info["punctuated_word"]

        previous_confidence = current_confidences[-1] if current_confidences else 0
        confidence_dropped = word_confidence < confidence_threshold * previous_confidence
        if confidence_dropped:
            log.debug(
                "Speaker confidence dropped from %s to %s for '%s'",
                previous_confidence,
                word_confidence,
                punctuated_word,
            )

        # Start a new segment at the start, when the speaker changes, or when confidence drops significantly.
        if current_speaker is None:
            # Initialize for the very first word.
            current_speaker = word_speaker
            segment_start = word_start
        elif current_speaker != word_speaker or confidence_dropped:
            average_confidence = (
                sum(current_confidences) / len(current_confidences) if current_confidences else 0
            )
            speaker_segments.append(
                SpeakerSegment(
                    words=current_text,
                    start=segment_start,
                    end=segment_end,
                    speaker=current_speaker,
                    average_confidence=average_confidence,
                )
            )
            # Reset for new speaker segment.
            current_text = []
            current_confidences = []
            current_speaker = word_speaker
            segment_start = word_start

        # Append current word to the segment.
        current_text.append((word_start, punctuated_word))
        current_confidences.append(word_confidence)
        segment_end = word_end

    # Append the last speaker's segment.
    if current_text and current_confidences:
        average_confidence = sum(current_confidences) / len(current_confidences)
        speaker_segments.append(
            SpeakerSegment(
                words=current_text,
                start=segment_start,
                end=segment_end,
                speaker=current_speaker,
                average_confidence=average_confidence,
            )
        )

    return speaker_segments
