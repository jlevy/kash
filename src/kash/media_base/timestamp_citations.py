from chopdiff.html import html_a, html_span

from kash.media_base.media_services import timestamp_media_url
from kash.utils.common.url import Url

## Formatting

NBSP = "\u00a0"

DATA_SOURCE_PATH = "data-src"
"""Path to a source file."""

DATA_TIMESTAMP = "data-timestamp"
"""Timestamp into an audio or video."""

DATA_SPEAKER_ID = "data-speaker-id"
"""Identifier for a speaker."""


SPEAKER_LABEL = "speaker-label"
"""Inline class name for a speaker."""

CITATION = "citation"
"""Inline class name for a citation."""

TIMESTAMP_LINK = "timestamp-link"
"""Inline class name for a timestamp link."""


def add_citation_to_text(text: str, citation: str) -> str:
    return f"{text}{NBSP}{citation}"


def format_timestamp(timestamp: float) -> str:
    hours, remainder = divmod(timestamp, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"
    else:
        return f"{int(minutes):02}:{int(seconds):02}"


def format_citation(citation: str) -> str:
    return html_span(f"{citation}", CITATION, safe=True)


def add_citation_to_sentence(
    old_sent: str, source_url: Url | None, source_path: str, timestamp: float
) -> str:
    return add_citation_to_text(
        old_sent, format_timestamp_citation(source_url, source_path, timestamp)
    )


def format_timestamp_citation(
    base_url: Url | None, source_path: str, timestamp: float, emoji: str = "⏱️"
) -> str:
    formatted_timestamp = format_timestamp(timestamp)
    if base_url:
        timestamp_url = timestamp_media_url(base_url, timestamp)
        formatted_timestamp = html_a(formatted_timestamp, timestamp_url)

    return html_span(
        f"{emoji}{formatted_timestamp}&nbsp;",
        [CITATION, TIMESTAMP_LINK],
        attrs={DATA_SOURCE_PATH: source_path, DATA_TIMESTAMP: f"{timestamp:.2f}"},
        safe=True,
    )


def html_timestamp_span(text: str, timestamp: float, safe: bool = False) -> str:
    return html_span(text, attrs={DATA_TIMESTAMP: f"{timestamp:.2f}"}, safe=safe)


def html_speaker_id_span(text: str, speaker_id: str, safe: bool = False) -> str:
    return html_span(text, class_name=SPEAKER_LABEL, attrs={DATA_SPEAKER_ID: speaker_id}, safe=safe)


## Tests


def test_format_timestamp_span():
    assert html_timestamp_span("text", 123.456) == '<span data-timestamp="123.46">text</span>'
