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

    speakers = set(segment.speaker for segment in speaker_segments)
    if len(speakers) > 1:
        turns: list[str] = []
        previous_speaker: int | None = None
        for segment in speaker_segments:
            segment_text = _format_words(segment.words)
            if segment.speaker == previous_speaker:
                turns[-1] += f"\n{segment_text}"
            else:
                turns.append(
                    f"{html_speaker_id_span(f'SPEAKER {segment.speaker}:', str(segment.speaker))}\n{segment_text}"
                )
                previous_speaker = segment.speaker
        return "\n\n".join(turns)
    else:
        return "\n".join(_format_words(segment.words) for segment in speaker_segments)


## Tests


def test_format_words_uses_single_line_breaks_between_sentences() -> None:
    formatted = _format_words(
        [
            (1.0, "First"),
            (1.5, "sentence."),
            (2.0, "Second"),
            (2.5, "sentence."),
        ]
    )

    assert formatted == (
        '<span data-timestamp="1.50">First sentence.</span>\n'
        '<span data-timestamp="2.50">Second sentence.</span>'
    )


def test_format_speaker_segments_uses_paragraph_breaks_only_for_speaker_changes() -> None:
    segments = [
        SpeakerSegment([(1.0, "First.")], 1.0, 1.5, 0, 0.9),
        SpeakerSegment([(2.0, "Still"), (2.5, "speaking.")], 2.0, 2.5, 0, 0.9),
        SpeakerSegment([(3.0, "Reply.")], 3.0, 3.5, 1, 0.9),
    ]

    formatted = format_speaker_segments(segments)

    assert formatted.count("SPEAKER 0:") == 1
    assert formatted.count("SPEAKER 1:") == 1
    assert (
        '<span data-timestamp="1.00">First.</span>\n'
        '<span data-timestamp="2.50">Still speaking.</span>'
    ) in formatted
    assert '</span>\n\n<span class="speaker-label" data-speaker-id="1">' in formatted
