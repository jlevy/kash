from functools import cache

from chopdiff.docs import is_word
from inflect import engine


@cache
def inflect():
    return engine()


def plural(word: str, count: int | None = None) -> str:
    """
    Pluralize a word.
    """
    if not is_word(word):
        return word
    return inflect().plural(word, count)  # pyright: ignore
