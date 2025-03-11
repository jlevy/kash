from collections.abc import Callable

from rich.console import Console
from rich.text import Text


def text_char_transform(text: Text, transform: Callable[[str], str]) -> Text:
    """
    Convert a Text object while preserving all styling.
    For characters where case conversion changes length (like 'ß' -> 'SS'),
    this will adjust spans to match the new text.

    The transform should be a function (like `str.upper` or `str.lower`) that
    works consistently with characters and strings, i.e., it is character-wise
    distributive: `transform(s) == "".join(transform(char) for char in s)` for
    any string `s`.
    """
    old_plain = text.plain
    new_plain = transform(old_plain)

    if len(new_plain) == len(old_plain):
        # Fast path: no length change.
        new_text = text.copy()
        new_text.plain = new_plain
        return new_text

    # Slower path: length changed, so need to adjust spans.
    result = text.blank_copy()

    old_pos = 0
    new_pos = 0

    # Build the new plain text and position map of old to new positions.
    pos_map = {}
    new_chars = [transform(char) for char in old_plain]
    old_pos, new_pos = 0, 0
    plain_result = ""
    for new_char in new_chars:
        plain_result += new_char
        pos_map[old_pos] = new_pos
        old_pos += 1
        new_pos += len(new_char)
    pos_map[len(old_plain)] = len(plain_result)

    result.plain = plain_result

    # Adjust spans based on new positions.
    for span in text.spans:
        new_start = pos_map.get(span.start, 0)
        new_end = pos_map.get(span.end)
        result.stylize(span.style, new_start, new_end)

    return result


def text_upper(text: Text) -> Text:
    return text_char_transform(text, str.upper)


def text_lower(text: Text) -> Text:
    return text_char_transform(text, str.lower)


## Tests


def test_text_upper():
    console = Console()

    # Test with special Unicode characters
    text = Text("Testing ß and ﬃ. More text.")
    text.stylize("bold red", 0, 7)  # "Testing"
    text.stylize("blue", 8, 9)  # "ß"
    text.stylize("green", 10, 13)  # "and"
    text.stylize("yellow", 14, 15)  # "ﬃ"
    text.stylize("italic", 16, 17)  # "."

    new_text = text_upper(text)

    console.print("\nOld Text:", text)
    console.print("New Text:", new_text)

    assert new_text.plain == "TESTING SS AND FFI. MORE TEXT."
    assert new_text.spans[1].start == 8
    assert new_text.spans[1].end == 10
    assert new_text.spans[2].start == 11
    assert new_text.spans[2].end == 14
    assert new_text.spans[3].start == 15
    assert new_text.spans[3].end == 18
