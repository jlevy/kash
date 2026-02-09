from __future__ import annotations

from typing import NamedTuple

from kash.config.logger import CustomLogger, get_logger
from kash.media_base.timestamp_citations import html_speaker_id_span, html_timestamp_span

log: CustomLogger = get_logger(__name__)


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


class SpeakerSegment(NamedTuple):
    words: list[tuple[float, str]]
    start: float
    end: float
    speaker: int
    average_confidence: float


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
