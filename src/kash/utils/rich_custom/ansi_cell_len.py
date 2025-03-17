from collections.abc import Callable
from functools import lru_cache

from rich.cells import _is_single_cell_widths, get_character_cell_size


def _strip_control_sequences(text: str) -> str:
    """Strips ANSI control sequences, including OSC-8 links, from the text."""
    from rich.ansi import _ansi_tokenize

    plain_text_parts = []
    for token in _ansi_tokenize(text):
        if token.plain:
            plain_text_parts.append(token.plain)
    return "".join(plain_text_parts)


@lru_cache(4096)  # noqa: F821
def _cached_cell_len(text: str) -> int:
    if _is_single_cell_widths(text):
        return len(text)
    return sum(map(get_character_cell_size, _strip_control_sequences(text)))


def ansi_cell_len(text: str, _cell_len: Callable[[str], int] = _cached_cell_len) -> int:
    """
    Same as Rich's `cell_len` method, but with control character stripping
    so that the visual length of OSC-8 links is correctly calculated.
    """
    if len(text) < 512:
        return _cell_len(text)
    if _is_single_cell_widths(text):
        return len(text)
    return sum(map(get_character_cell_size, _strip_control_sequences(text)))


## Tests


def _make_osc_link(url: str, text: str) -> str:
    return f"\x1b]8;;{url}\x1b\\{text}\x1b]8;;\x1b\\"


_plain_text = "ansi🤔"
_short_osc_link = _make_osc_link("http://example.com/", _plain_text)
_long_osc_link = _make_osc_link("http://example.com/" + "x" * 100, _plain_text)


# This is somewhat unexpected behavior of Rich's default cell_len method:
def test_rich_default_cell_len():
    from rich.cells import cell_len

    print(
        f"old lengths: plain_text={cell_len(_plain_text)} "
        f"short_osc_link={cell_len(_short_osc_link)} "
        f"long_osc_link={cell_len(_long_osc_link)}"
    )
    assert cell_len(_plain_text) == 6
    assert cell_len(_short_osc_link) == 35  # Wrong!
    assert cell_len(_long_osc_link) == 135  # Wrong!


# This is the behavior we want:
def test_ansi_cell_len():
    print(
        f"new lengths: plain_text={ansi_cell_len(_plain_text)} "
        f"short_osc_link={ansi_cell_len(_short_osc_link)} "
        f"long_osc_link={ansi_cell_len(_long_osc_link)}"
    )
    assert ansi_cell_len(_plain_text) == 6
    assert ansi_cell_len(_short_osc_link) == ansi_cell_len(_plain_text)
    assert ansi_cell_len(_long_osc_link) == ansi_cell_len(_plain_text)
