import re
from functools import cache

from kash.config.logger import get_logger
from kash.docs.load_help_topics import load_help_topics
from kash.help.help_types import Faq

log = get_logger(__name__)


def extract_heading_body_pairs(markdown_text: str, heading_chars: str = "###") -> list[Faq]:
    """
    Extract headings and body text pairs from markdown text.
    Each heading starts with the specified heading characters and the body text is all text
    until the next heading of the same level.
    """
    # Escape heading chars for regex and build pattern.
    heading_pattern = f"^{re.escape(heading_chars)}\\s+"

    # Split by headings, skip the first part (intro)
    sections = re.split(heading_pattern, markdown_text, flags=re.MULTILINE)[1:]

    faqs = []
    for section in sections:
        if not section.strip():
            continue

        # Split into question and answer at first newline
        parts = section.split("\n", 1)
        if len(parts) != 2:
            continue

        question = parts[0].strip()
        # Get all text until next heading of same level
        answer = re.split(heading_pattern, parts[1], flags=re.MULTILINE)[0].strip()

        faqs.append(Faq(question=question, answer=answer))

    return faqs


@cache
def load_faqs() -> list[Faq]:
    """
    Load all FAQs from the help topics.
    """
    help_topics = load_help_topics()
    return extract_heading_body_pairs(str(help_topics.faq))
