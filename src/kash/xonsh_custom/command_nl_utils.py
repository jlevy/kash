from __future__ import annotations

import re

from prettyfmt import fmt_words

INNER_PUNCT_CHARS = r"-'’–—"
OUTER_PUNCT_CHARS = r".,'\"" "''':;!?()"

ESCAPED_INNER_PUNCT_CHARS = re.escape(INNER_PUNCT_CHARS)
ESCAPED_OUTER_PUNCT_CHARS = re.escape(OUTER_PUNCT_CHARS)

PUNCT_SEQ_RE = re.compile(rf"[{ESCAPED_INNER_PUNCT_CHARS}{ESCAPED_OUTER_PUNCT_CHARS}]+")

ONLY_WORDS_RE = re.compile(rf"^[\w\s{ESCAPED_INNER_PUNCT_CHARS}]*$")

PLAIN_WORD_RE = re.compile(r"^\w.*\w$")


def as_nl_words(text: str) -> str:
    """
    Break a text into words, dropping common punctuation and whitespace but
    leaving other chars like filenames, code, etc.
    """
    words = [word.strip(OUTER_PUNCT_CHARS + " ") or word for word in text.split()]
    return fmt_words(*words)


def looks_like_nl(text: str) -> bool:
    """
    Check if a text looks like plain natural language text. Just very simple
    based on words and only basic punctuation.
    """
    is_only_word_chars = bool(ONLY_WORDS_RE.fullmatch(text))
    without_punct = PUNCT_SEQ_RE.sub("", text)
    is_only_words_punct = bool(ONLY_WORDS_RE.fullmatch(without_punct))
    words = without_punct.strip().split()
    one_longer_word = any(len(word) > 3 for word in words)

    return one_longer_word and (
        (is_only_words_punct and len(words) >= 3) or (is_only_word_chars and len(words) >= 2)
    )


## Tests


def test_as_nl_words():
    assert as_nl_words("x=3+9; foo('bar')") == "x=3+9 foo('bar"
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
    assert looks_like_nl("is this a question?")
    assert looks_like_nl("'quoted text'")
    assert looks_like_nl("git push origin main")
    assert looks_like_nl("this is natural language")
    assert looks_like_nl(" what's up, doc? ")
    assert looks_like_nl("multiple   spaces   here")
    assert looks_like_nl("go to the store (buy milk)")
    assert looks_like_nl("'quoted text' has three words")
    assert looks_like_nl("git push origin main")
    assert looks_like_nl("what's up")

    assert not looks_like_nl("hello-world")
    assert not looks_like_nl("cd ..")
    assert not looks_like_nl("file_name.txt")
    assert not looks_like_nl("ls -la")
    assert not looks_like_nl("https://example.com")
    assert not looks_like_nl("cmd | grep pattern")
    assert not looks_like_nl("use a+b")
    assert not looks_like_nl("x=3")
    assert not looks_like_nl("a > b")
    assert not looks_like_nl("file_name.txt")
    assert not looks_like_nl("foo;")
    assert not looks_like_nl("hello-world")
    assert not looks_like_nl("ls -la")
    assert not looks_like_nl("cd ..")
    assert not looks_like_nl("echo $HOME")
    assert not looks_like_nl("https://example.com")
    assert not looks_like_nl(text="file.txt")
    assert not looks_like_nl("cmd | grep pattern")
