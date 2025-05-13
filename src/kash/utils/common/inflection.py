from functools import cache


@cache
def inflect():
    # Load lazily. This takes almost a full second to import!
    from inflect import engine

    return engine()


def plural(word: str, count: int | None = None) -> str:
    """
    Pluralize a word.
    """
    from chopdiff.docs import is_word

    if not is_word(word):
        return word
    return inflect().plural(word, count)  # pyright: ignore
