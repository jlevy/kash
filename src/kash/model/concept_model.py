from typing import NewType

from kash.utils.lang_utils.capitalization import capitalize_cms

Concept = NewType("Concept", str)


def canonicalize_concept(concept: str, capitalize: bool = True) -> Concept:
    """
    Convert a concept string (general name, person, etc.) to a canonical form.
    Drop any extraneous Markdown bullets. Drop any quoted phrases (e.g. book titles etc)
    for consistency.
    """
    concept = concept.strip("-* ")
    for quote in ['"', "'"]:
        if concept.startswith(quote) and concept.endswith(quote):
            concept = concept[1:-1]
    if capitalize:
        return Concept(capitalize_cms(concept))
    else:
        return Concept(concept)


def normalize_concepts(
    concepts: list[str], sort_dedup: bool = True, capitalize: bool = True
) -> list[Concept]:
    if sort_dedup:
        return sorted(set(canonicalize_concept(concept, capitalize) for concept in concepts))
    else:
        return [canonicalize_concept(concept, capitalize) for concept in concepts]
