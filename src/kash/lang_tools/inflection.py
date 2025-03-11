from functools import cache
from typing import Optional

from chopdiff.docs import is_word
from inflect import engine


@cache
def inflect():
    return engine()


def plural(word: str, count: Optional[int] = None) -> str:
    """
    Pluralize a word.
    """
    if not is_word(word):
        return word
    return inflect().plural(word, count)  # type: ignore
