from os.path import getsize
from pathlib import Path
from typing import NamedTuple

from httpx import Timeout
from openai import OpenAI

from kash.config.api_keys import load_dotenv_paths
from kash.config.logger import CustomLogger, get_logger
from kash.media_base.timestamp_citations import html_speaker_id_span, html_timestamp_span
from kash.utils.errors import ContentError

log: CustomLogger = get_logger(__name__)


def openai_whisper_transcribe_audio_small(audio_file_path: str) -> str:
    """
    Transcribe an audio file. Whisper is very good quality but (as of 2024-05)
    OpenAI's version does not support diarization and must be under 25MB.

    https://help.openai.com/en/articles/7031512-whisper-api-faq
    """
    WHISPER_MAX_SIZE = 25 * 1024 * 1024

    size = getsize(audio_file_path)
    if size > WHISPER_MAX_SIZE:
        raise ValueError("Audio file too large for Whisper (%s > %s)" % (size, WHISPER_MAX_SIZE))
    log.info(
        "Transcribing via Whisper: %s (size %s)",
        audio_file_path,
        size,
    )

    client = OpenAI()
    with open(audio_file_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            # For when we want timestamps:
            # response_format="verbose_json",
            # timestamp_granularities=["word"]
        )
        text = transcription.text
    return text


class SpeakerSegment(NamedTuple):
    words: list[tuple[float, str]]
    start: float
    end: float
    speaker: int
    average_confidence: float


def deepgram_transcribe_audio(audio_file_path: Path, language: str | None = None) -> str:
    """
    Transcribe an audio file using Deepgram.
    """
    from deepgram import ClientOptionsFromEnv, DeepgramClient, FileSource, PrerecordedOptions

    size = getsize(audio_file_path)
    log.info(
        "Transcribing via Deepgram (language %r): %s (size %s)", language, audio_file_path, size
    )

    load_dotenv_paths()
    deepgram = DeepgramClient("", ClientOptionsFromEnv())

    with open(audio_file_path, "rb") as audio_file:
        buffer_data = audio_file.read()

    payload: FileSource = {
        "buffer": buffer_data,
    }

    options = PrerecordedOptions(model="nova-2", smart_format=True, diarize=True, language=language)
    response = deepgram.listen.rest.v("1").transcribe_file(payload, options, timeout=Timeout(500))  # pyright: ignore

    log.save_object("Deepgram response", None, response)

    diarized_segments = _deepgram_diarized_segments(response)
    log.debug("Diarized response: %s", diarized_segments)

    if not diarized_segments:
        raise ContentError(
            f"No speaker segments found in Deepgram response (are voices silent or missing?): {audio_file_path}"
        )

    formatted_segments = format_speaker_segments(diarized_segments)

    return formatted_segments


def _deepgram_diarized_segments(data, confidence_threshold=0.3) -> list[SpeakerSegment]:
    """Process Deepgram diarized results into text segments per speaker."""

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


def _is_new_sentence(word: str, next_word: str | None) -> bool:
    return (
        (word.endswith(".") or word.endswith("?") or word.endswith("!"))
        and next_word is not None
        and next_word[0].isupper()
    )


def _format_words(words: list[tuple[float, str]], include_sentence_timestamps=True) -> str:
    """Format words with timestamps added in spans."""

    if not words:
        return ""

    sentences = []
    current_sentence = []
    for i, (timestamp, word) in enumerate(words):
        current_sentence.append(word)
        next_word = words[i + 1][1] if i + 1 < len(words) else None
        if _is_new_sentence(word, next_word):
            sentences.append((timestamp, current_sentence))
            current_sentence = []

    if current_sentence:
        sentences.append((words[-1][0], current_sentence))

    formatted_text = []
    for timestamp, sentence in sentences:
        formatted_sentence = " ".join(sentence)
        if include_sentence_timestamps:
            formatted_text.append(html_timestamp_span(formatted_sentence, timestamp))
        else:
            formatted_text.append(formatted_sentence)

    return "\n".join(formatted_text)


def format_speaker_segments(speaker_segments: list[SpeakerSegment]) -> str:
    """
    Format speaker segments in a simple HTML format with <span> tags including speaker
    ids and timestamps.
    """

    # Use \n\n for readability between segments so each speaker is its own
    # paragraph.
    SEGMENT_SEP = "\n\n"

    speakers = set(segment.speaker for segment in speaker_segments)
    if len(speakers) > 1:
        lines = []
        for segment in speaker_segments:
            lines.append(
                f"{html_speaker_id_span(f'SPEAKER {segment.speaker}:', str(segment.speaker))}\n{_format_words(segment.words)}"
            )
        return SEGMENT_SEP.join(lines)
    else:
        return SEGMENT_SEP.join(_format_words(segment.words) for segment in speaker_segments)
