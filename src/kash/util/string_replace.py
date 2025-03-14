from typing import TypeAlias

Insertion = tuple[int, str]


def insert_multiple(text: str, insertions: list[Insertion]) -> str:
    """
    Insert multiple strings into `text` at the given offsets, at once.
    """
    chunks = []
    last_end = 0
    for offset, insertion in sorted(insertions, key=lambda x: x[0]):
        chunks.append(text[last_end:offset])
        chunks.append(insertion)
        last_end = offset
    chunks.append(text[last_end:])
    return "".join(chunks)


Replacement: TypeAlias = tuple[int, int, str]


def replace_multiple(text: str, replacements: list[Replacement]) -> str:
    """
    Replace multiple substrings in `text` with new strings, simultaneously.
    The replacements are a list of tuples (start_offset, end_offset, new_string).
    """
    replacements = sorted(replacements, key=lambda x: x[0])
    chunks = []
    last_end = 0
    for start, end, new_text in replacements:
        if start < last_end:
            raise ValueError("Overlapping replacements are not allowed.")
        chunks.append(text[last_end:start])
        chunks.append(new_text)
        last_end = end
    chunks.append(text[last_end:])
    return "".join(chunks)


## Tests


def test_insert_multiple():
    text = "hello world"
    insertions = [(5, ",")]
    expected = "hello, world"
    assert insert_multiple(text, insertions) == expected, "Single insertion failed"

    text = "hello world"
    insertions = [(0, "Start "), (11, " End")]
    expected = "Start hello world End"
    assert insert_multiple(text, insertions) == expected, "Multiple insertions failed"

    text = "short"
    insertions = [(10, " end")]
    expected = "short end"
    assert insert_multiple(text, insertions) == expected, "Out of bounds insertion failed"

    text = "negative test"
    insertions = [(-1, "ss")]
    expected = "negative tessst"
    assert insert_multiple(text, insertions) == expected, "Negative offset insertion failed"

    text = "no change"
    insertions = []
    expected = "no change"
    assert insert_multiple(text, insertions) == expected, "Empty insertions failed"


def test_replace_multiple():
    text = "The quick brown fox"
    replacements = [(4, 9, "slow"), (16, 19, "dog")]
    expected = "The slow brown dog"
    assert replace_multiple(text, replacements) == expected, "Multiple replacements failed"

    text = "overlap test"
    replacements = [(0, 6, "start"), (5, 10, "end")]
    try:
        replace_multiple(text, replacements)
        raise AssertionError("Overlapping replacements did not raise ValueError")
    except ValueError:
        pass  # Expected exception

    text = "short text"
    replacements = [(5, 10, " longer text")]
    expected = "short longer text"
    assert replace_multiple(text, replacements) == expected, "Out of bounds replacement failed"

    text = "no change"
    replacements = []
    expected = "no change"
    assert replace_multiple(text, replacements) == expected, "Empty replacements failed"
