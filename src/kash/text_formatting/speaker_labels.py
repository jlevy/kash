from typing import List

from chopdiff.html import html_extract_attribute_value, html_find_tag, TagMatch

from kash.exec.precondition_registry import register_precondition
from kash.model.items_model import Item
from kash.text_formatting.citations import DATA_SPEAKER_ID


@register_precondition
def has_speaker_ids(item: Item) -> bool:
    return bool(item.body and extract_speaker_id(item.body))


def extract_speaker_id(html_string: str):
    return html_extract_attribute_value(DATA_SPEAKER_ID)(html_string)


def find_speaker_labels(html_string: str) -> List[TagMatch]:
    """
    Find all speaker labels with their offsets in the HTML string.
    This function looks for elements with a `data-speaker-id` attribute.
    """
    return html_find_tag(html_string, attr_name=DATA_SPEAKER_ID)


## Tests


def test_extract_speaker_id():
    html_with_speaker = '<span class="speaker-label" data-speaker-id="1">SPEAKER 1:</span>'
    assert extract_speaker_id(html_with_speaker) == "1"

    html_without_speaker = "<span>SPEAKER 1:</span>"
    assert extract_speaker_id(html_without_speaker) is None


def test_find_speaker_labels():
    html_string = """
    <span class="speaker-label" data-speaker-id="1">Speaker 1:</span>
    <p>First line of dialogue.</p>
    <span class="speaker-label" data-speaker-id="2">Speaker 2:</span>
    <p>Second line of dialogue.</p>
    <span class="speaker-label" data-speaker-id="3">Speaker 3:</span>
    <p>Third line of dialogue.</p>
    """
    matches = find_speaker_labels(html_string)
    assert len(matches) == 3

    assert matches[0].attribute_value == "1"
    assert matches[0].inner_text.strip() == "Speaker 1:"
    assert matches[1].attribute_value == "2"
    assert matches[1].inner_text.strip() == "Speaker 2:"
    assert matches[2].attribute_value == "3"
    assert matches[2].inner_text.strip() == "Speaker 3:"
