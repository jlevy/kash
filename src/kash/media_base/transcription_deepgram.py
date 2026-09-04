from __future__ import annotations

from os.path import getsize
from pathlib import Path
from typing import TYPE_CHECKING

from clideps.env_vars.dotenv_utils import load_dotenv_paths

from kash.config.logger import CustomLogger, get_logger
from kash.config.settings import global_settings
from kash.media_base.transcription_format import SpeakerSegment, format_speaker_segments
from kash.utils.common.format_utils import fmt_path
from kash.media_base.transcription_settings import TranscriptionSettings
from kash.utils.errors import ContentError

if TYPE_CHECKING:
    from deepgram.types.listen_v1accepted_response import ListenV1AcceptedResponse
    from deepgram.types.listen_v1response import ListenV1Response

log: CustomLogger = get_logger(__name__)

# Deepgram batch transcription runs at roughly an order of magnitude faster than
# realtime, but the request must also carry the upload and the provider's queue. A
# fixed timeout works for clips and silently caps long media: a multi-hour file can
# spend minutes uploading and processing and then abort with a timeout rather than a
# usable error. Scale the budget with the audio instead, from a floor that keeps short
# files responsive.
TRANSCRIPTION_TIMEOUT_FLOOR_S = 500.0
"""Minimum request budget, which is also what short files use."""

TRANSCRIPTION_TIMEOUT_PER_AUDIO_HOUR_S = 900.0
"""Additional budget per hour of audio."""

TRANSCRIPTION_TIMEOUT_CEILING_S = 7200.0
"""Upper bound, so a corrupt or absurd duration cannot hang a run indefinitely."""


def transcription_timeout(audio_duration_s: float | None) -> float:
    """
    Request timeout for transcribing audio of the given duration.

    Returns the floor when the duration is unknown, so callers that cannot probe the
    audio behave exactly as before.
    """
    if not audio_duration_s or audio_duration_s <= 0:
        return TRANSCRIPTION_TIMEOUT_FLOOR_S
    budget = (
        TRANSCRIPTION_TIMEOUT_FLOOR_S
        + (audio_duration_s / 3600.0) * TRANSCRIPTION_TIMEOUT_PER_AUDIO_HOUR_S
    )
    return min(budget, TRANSCRIPTION_TIMEOUT_CEILING_S)


def deepgram_transcribe_raw(
    audio_file_path: Path,
    language: str | None = None,
    *,
    settings: TranscriptionSettings | None = None,
    audio_duration_s: float | None = None,
) -> ListenV1Response | ListenV1AcceptedResponse:
    """
    Transcribe an audio file using Deepgram and return the raw response.
    """
    # Slow import, do lazily.
    from deepgram import DeepgramClient
    from deepgram.core.request_options import RequestOptions

    settings = settings or TranscriptionSettings.create(language=language)
    size = getsize(audio_file_path)
    log.info(
        "Transcribing via Deepgram (settings %r): %s (size %s)",
        settings,
        audio_file_path,
        size,
    )

    load_dotenv_paths(True, True, global_settings().system_config_dir)
    deepgram = DeepgramClient()

    timeout_s = transcription_timeout(audio_duration_s)
    log.message(
        "Transcribing %s of audio with a %s second request budget: %s",
        f"{audio_duration_s / 60:.0f} min" if audio_duration_s else "unknown duration",
        f"{timeout_s:.0f}",
        fmt_path(audio_file_path),
    )

    with open(audio_file_path, "rb") as audio_file:
        buffer_data = audio_file.read()

    response = deepgram.listen.v1.media.transcribe_file(
        request=buffer_data,
        model=settings.model,
        smart_format=settings.smart_format,
        diarize_model=settings.diarize_model,
        language=settings.language,
        keyterm=list(settings.key_terms) or None,
        request_options=RequestOptions(timeout_in_seconds=timeout_s),
    )

    return response


def deepgram_transcribe_audio(
    audio_file_path: Path,
    language: str | None = None,
    *,
    settings: TranscriptionSettings | None = None,
    audio_duration_s: float | None = None,
) -> str:
    response = deepgram_transcribe_raw(
        audio_file_path, language, settings=settings, audio_duration_s=audio_duration_s
    )

    log.save_object("Deepgram response", None, response)

    # Convert Pydantic model to dict for processing.
    response_dict = response.model_dump()
    diarized_segments = _deepgram_diarized_segments(response_dict)
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
