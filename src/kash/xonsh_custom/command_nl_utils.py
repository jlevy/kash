import re

from prettyfmt import fmt_words

INNER_PUNCT_CHARS = r"-'’–—"
OUTER_PUNCT_CHARS = r".,'\"“”‘’:!?()"

WORD_PAT = (
    rf"[{OUTER_PUNCT_CHARS}]{{0,2}}[\w]+(?:[{INNER_PUNCT_CHARS}\w]+)*[{OUTER_PUNCT_CHARS}]{{0,2}}"
)
"""
Pattern to match a word in natural language text (i.e. words and natural
language-only punctuation).
"""

NL_PAT = rf"^{WORD_PAT}(?:\s+{WORD_PAT})*$"
"""
Pattern to match natural language text in a command line.
"""


def as_nl_words(text: str) -> str:
    """
    Break a text into words, dropping common punctuation and whitespace but
    leaving other chars like filenames, code, etc.
    """
    words = [word.strip(OUTER_PUNCT_CHARS + " ") or word for word in text.split()]
    return fmt_words(*words)


def looks_like_nl(text: str) -> bool:
    """
    Check if a text looks like plain natural language text, i.e. word chars,
    possibly with ? or hyphens/apostrophes when inside words but not other
    code or punctuation.
    """
    return bool(re.match(NL_PAT, text.strip()))


## Tests


def test_as_nl_words():
    assert as_nl_words("x=3+9; foo('bar')") == "x=3+9; foo('bar"
    assert as_nl_words("cd ..") == "cd .."
    assert as_nl_words("transcribe some-file_23.mp3") == "transcribe some-file_23.mp3"
    assert as_nl_words("hello world ") == "hello world"
    assert as_nl_words("hello, world!") == "hello world"
    assert as_nl_words("  hello   world  ") == "hello world"
    assert as_nl_words("'hello' \"world\"") == "hello world"
    assert as_nl_words("hello-world") == "hello-world"
    assert as_nl_words("what's up?") == "what's up"
    assert as_nl_words("multiple   spaces   here") == "multiple spaces here"


def test_looks_like_nl():
    assert looks_like_nl("hello world")
    assert looks_like_nl(" hello world ")
    assert looks_like_nl("what's up")
    assert looks_like_nl("hello-world")
    assert looks_like_nl("is this a question?")
    assert looks_like_nl("'quoted text'")
    assert looks_like_nl("git push origin main")

    assert not looks_like_nl("ls -la")
    assert not looks_like_nl("cd ..")
    assert not looks_like_nl("echo $HOME")
    assert not looks_like_nl("https://example.com")
    assert not looks_like_nl("file.txt")
    assert not looks_like_nl("cmd | grep pattern")
