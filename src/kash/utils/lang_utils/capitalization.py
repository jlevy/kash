"""
Tools for capitalizing words and phrases.
"""

# TODO: May be better to replace or merge this, which also has a good test suite
# https://github.com/ppannuto/python-titlecase

import re

language_rules = {
    "en": {
        "small_words": [
            "a",
            "an",
            "and",
            "as",
            "at",
            "but",
            "by",
            "for",
            "if",
            "in",
            "nor",
            "of",
            "on",
            "or",
            "so",
            "the",
            "to",
            "up",
            "yet",
            "with",
            "from",
        ],
        "name_particles": ["de", "la", "van", "von", "der", "den", "ter", "ten"],
        "always_cap": [
            "PDF",
            "URL",
            "HTML",
            "CSS",
            "API",
            "XML",
            "JSON",
            "SQL",
            "CSV",
            "FTP",
            "TCP",
            "CLI",
        ],
    },
}


def capitalize(word: str) -> str:
    """
    Cap first letter but leave rest unchanged.
    """
    return word[0].upper() + word[1:]


def capitalize_cms(
    phrase: str,
    language: str = "en",
    underscores_to_spaces: bool = False,
) -> str:
    """
    Capitalize a word, phrase, or title according to the Chicago Manual of Style rules
    for titles.

    Trims whitespace. Does not lowercase words, so it is safe with acronyms and other
    odd capitalizations.

    Also give a best effort to respect names with particles like "de", "la", "van", "von",
    "der", "den", "ter", "ten".
    """
    if language not in language_rules:
        raise ValueError(f"Unsupported language: {language}")

    if underscores_to_spaces:
        phrase = " ".join(re.split("_+", phrase))

    small_words = language_rules[language]["small_words"]
    name_particles = language_rules[language]["name_particles"]
    always_cap = language_rules[language]["always_cap"]

    words = phrase.split()
    capitalized_title = []

    for i, word in enumerate(words):
        if word.upper() in always_cap:
            capitalized_title.append(word.upper())
        elif i == 0 or i == len(words) - 1 or word.lower() not in small_words + name_particles:
            capitalized_title.append(capitalize(word))
        else:
            capitalized_title.append(word)

    return " ".join(capitalized_title)


## Tests


def test_capitalize_cms():
    assert capitalize_cms("ALL CAPS") == "ALL CAPS"
    assert capitalize_cms("lower case") == "Lower Case"
    assert (
        capitalize_cms("an example of a title that should follow chicago manual of style rules")
        == "An Example of a Title That Should Follow Chicago Manual of Style Rules"
    )
    assert (
        capitalize_cms("the quick brown fox jumps over the lazy dog")
        == "The Quick Brown Fox Jumps Over the Lazy Dog"
    )
    assert capitalize_cms("to be or not to be") == "To Be or Not to Be"
    assert capitalize_cms("a study in scarlet") == "A Study in Scarlet"
    assert capitalize_cms("by the riverbank") == "By the Riverbank"
    assert capitalize_cms("the girl with the dragon tattoo") == "The Girl with the Dragon Tattoo"
    assert (
        capitalize_cms("the rise and fall of ziggy stardust and the spiders from mars")
        == "The Rise and Fall of Ziggy Stardust and the Spiders from Mars"
    )
    assert capitalize_cms("a visit to the van gogh museum") == "A Visit to the van Gogh Museum"
    assert capitalize_cms("the works of de la cruz") == "The Works of de la Cruz"
    assert capitalize_cms("ludwig van beethoven") == "Ludwig van Beethoven"
    assert capitalize_cms("the NASA mission to Mars") == "The NASA Mission to Mars"

    assert capitalize_cms("generate_pdf", underscores_to_spaces=True) == "Generate PDF"
    assert capitalize_cms("snake_case__1", underscores_to_spaces=True) == "Snake Case 1"
