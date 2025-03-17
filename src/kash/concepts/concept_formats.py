from kash.text_handling.markdown_util import extract_bullet_points
from kash.utils.lang_utils.capitalization import capitalize_cms


def canonicalize_concept(concept: str) -> str:
    """
    Convert a concept string (general name, person, etc.) to a canonical form.
    Drop any extraneous Markdown bullets.
    """
    return capitalize_cms(concept.strip("-* "))


def normalize_concepts(concepts: list[str]) -> list[str]:
    return sorted(set(canonicalize_concept(concept) for concept in concepts))


def concepts_from_bullet_points(markdown_text: str) -> list[str]:
    """
    Parse, normalize, capitalize, sort, and then remove exact duplicates from a Markdown
    list of concepts as bullet points.
    """
    concepts = extract_bullet_points(markdown_text)
    return normalize_concepts(concepts)
