from functools import cache

# Had been using the `inflect` package, but it takes over 1s to import.
# pluralizer seems simpler and fine for common English usage.


@cache
def _get_pluralizer():
    from pluralizer import Pluralizer

    return Pluralizer()


def plural(word: str, count: int | None = None) -> str:
    """
    Pluralize or singularize a word based on the count.
    """
    from chopdiff.docs import is_word

    if not is_word(word):
        return word
    return _get_pluralizer().pluralize(word, count=count)
