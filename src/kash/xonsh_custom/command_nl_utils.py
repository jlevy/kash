import re

from prettyfmt import fmt_words

INNER_PUNCT_CHARS = "-'’–—"
OUTER_PUNCT_CHARS = "“”‘’:!?()"

INNER_PUNCT_PAT = rf"[{INNER_PUNCT_CHARS}]"
OUTER_PUNCT_PAT = rf"[{OUTER_PUNCT_CHARS}]"

WORD_PAT = rf"{OUTER_PUNCT_PAT}{0, 2}[\w]+(?:{INNER_PUNCT_PAT}[\w]+)*{OUTER_PUNCT_PAT}{0, 2}"
"""
Pattern to match a word in natural language text (i.e. words and natural
language-only punctuation).
"""

NL_PAT = rf"^{WORD_PAT}(?:\s+{WORD_PAT})$"
"""
Pattern to match natural language text in a command line.
"""


def as_nl_words(text: str) -> str:
    """
    Break a text into words, dropping punctuation and extra spaces.
    """
    return fmt_words(*(word.strip(OUTER_PUNCT_CHARS + " ") for word in text.split()))


def looks_like_nl(text: str) -> bool:
    """
    Check if a text looks like plain natural language text, i.e. word chars,
    possibly with ? or hyphens/apostrophes when inside words but not other
    code or punctuation.
    """
    return bool(re.match(NL_PAT, text))
