from kash.text_handling.markdown_utils import extract_bullet_points
from kash.utils.lang_utils.capitalization import capitalize_cms


def canonicalize_concept(concept: str, capitalize: bool = True) -> str:
    """
    Convert a concept string (general name, person, etc.) to a canonical form.
    Drop any extraneous Markdown bullets.
    """
    concept = concept.strip("-* ")
    if capitalize:
        return capitalize_cms(concept)
    else:
        return concept


def normalize_concepts(
    concepts: list[str], sort_dedup: bool = True, capitalize: bool = True
) -> list[str]:
    if sort_dedup:
        return sorted(set(canonicalize_concept(concept, capitalize) for concept in concepts))
    else:
        return [canonicalize_concept(concept, capitalize) for concept in concepts]


def concepts_from_bullet_points(
    markdown_text: str, sort_dedup: bool = True, capitalize: bool = True
) -> list[str]:
    """
    Parse, normalize, capitalize concepts as a Markdown bullet list. If sort_dedup is True,
    sort and remove exact duplicates.
    """
    concepts: list[str] = extract_bullet_points(markdown_text)
    return normalize_concepts(concepts, sort_dedup, capitalize)
