from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from flowmark import flowmark_markdown, line_wrap_by_sentence
from marko import Markdown
from marko.ext import footnote

from kash.utils.text_handling.markdown_utils import comprehensive_transform_tree


def _normalize_footnotes_in_markdown(content: str) -> str:
    """
    Ensure blank lines between consecutive footnote definitions.

    Marko has a bug where consecutive footnotes without blank lines are parsed
    as a single footnote. This adds blank lines where needed.
    """
    lines = content.split("\n")
    result = []
    i = 0

    while i < len(lines):
        line = lines[i]
        result.append(line)

        # Check if this is a footnote definition
        if re.match(r"^\[\^[^\]]+\]:", line):
            # Look ahead to see if the next non-empty line is also a footnote
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                result.append(lines[j])
                j += 1

            if j < len(lines) and re.match(r"^\[\^[^\]]+\]:", lines[j]):
                # Next non-empty line is also a footnote, add blank line
                result.append("")

            i = j
        else:
            i += 1

    return "\n".join(result)


@dataclass
class FootnoteInfo:
    """
    Information about a single footnote definition.
    """

    footnote_id: str  # The footnote ID with caret (e.g., "^123", "^foo")
    content: str  # The rendered markdown content of the footnote
    raw_element: footnote.FootnoteDef  # The original marko element


@dataclass
class MarkdownFootnotes:
    """
    Container for all footnotes in a markdown document with fast lookup.

    Provides efficient access to footnote definitions by their IDs.
    IDs are stored with the leading caret (^) to avoid collisions.
    """

    footnotes: dict[str, FootnoteInfo] = field(default_factory=dict)
    """Dictionary mapping footnote IDs (with ^) to FootnoteInfo objects."""

    @staticmethod
    def from_markdown(content: str, markdown_parser: Markdown | None = None) -> MarkdownFootnotes:
        """
        Extract all footnotes from markdown content.

        Args:
            content: The markdown content to parse
            markdown_parser: Optional custom markdown parser. If None, uses default flowmark setup.

        Returns:
            MarkdownFootnotes instance with all footnotes indexed by ID
        """
        if markdown_parser is None:
            markdown_parser = flowmark_markdown(line_wrap_by_sentence(is_markdown=True))

        # Normalize to work around marko bug with consecutive footnotes
        normalized_content = _normalize_footnotes_in_markdown(content)
        document = markdown_parser.parse(normalized_content)
        return MarkdownFootnotes.from_document(document, markdown_parser)

    @staticmethod
    def from_document(document: Any, markdown_parser: Markdown | None = None) -> MarkdownFootnotes:
        """
        Extract all footnotes from a parsed markdown document.

        Args:
            document: A parsed marko document object
            markdown_parser: The markdown parser used (needed for rendering).
                           If None, uses default flowmark setup.

        Returns:
            MarkdownFootnotes instance with all footnotes indexed by ID
        """
        if markdown_parser is None:
            markdown_parser = flowmark_markdown(line_wrap_by_sentence(is_markdown=True))

        footnotes_dict: dict[str, FootnoteInfo] = {}

        def collect_footnote(element: Any) -> None:
            if isinstance(element, footnote.FootnoteDef):
                content_parts = []
                if hasattr(element, "children") and element.children:
                    for child in element.children:
                        rendered = markdown_parser.renderer.render(child)
                        content_parts.append(rendered)

                rendered_content = "".join(content_parts).strip()

                footnote_id = f"^{element.label}"
                footnotes_dict[footnote_id] = FootnoteInfo(
                    footnote_id=footnote_id,
                    content=rendered_content,
                    raw_element=element,
                )

        comprehensive_transform_tree(document, collect_footnote)

        return MarkdownFootnotes(footnotes=footnotes_dict)

    def get(self, footnote_id: str, default: FootnoteInfo | None = None) -> FootnoteInfo | None:
        """
        Get a footnote by its ID.

        Args:
            footnote_id: The footnote ID (with or without leading ^)
            default: Default value if footnote not found

        Returns:
            FootnoteInfo if found, otherwise default value
        """
        if not footnote_id.startswith("^"):
            footnote_id = f"^{footnote_id}"
        return self.footnotes.get(footnote_id, default)

    def __getitem__(self, footnote_id: str) -> FootnoteInfo:
        """
        Get a footnote by its ID using dictionary-style access.

        Args:
            footnote_id: The footnote ID (with or without leading ^)

        Returns:
            FootnoteInfo for the ID

        Raises:
            KeyError: If the footnote ID is not found
        """
        if not footnote_id.startswith("^"):
            footnote_id = f"^{footnote_id}"
        return self.footnotes[footnote_id]

    def __contains__(self, footnote_id: str) -> bool:
        """
        Check if a footnote exists.

        Args:
            footnote_id: The footnote ID (with or without leading ^)
        """
        if not footnote_id.startswith("^"):
            footnote_id = f"^{footnote_id}"
        return footnote_id in self.footnotes

    def __len__(self) -> int:
        """Return the number of footnotes."""
        return len(self.footnotes)

    def __iter__(self):
        """Iterate over footnote IDs (with carets)."""
        return iter(self.footnotes)

    def items(self):
        """Return (footnote_id, FootnoteInfo) pairs."""
        return self.footnotes.items()

    def values(self):
        """Return FootnoteInfo objects."""
        return self.footnotes.values()

    def keys(self):
        """Return footnote IDs (with carets)."""
        return self.footnotes.keys()


def extract_footnote_references(content: str, markdown_parser: Markdown | None = None) -> list[str]:
    """
    Extract all footnote reference IDs used in the content.

    This finds all FootnoteRef elements (e.g., [^123] in the text) as opposed
    to FootnoteDef elements which are the definitions.

    Args:
        content: The markdown content to parse
        markdown_parser: Optional custom markdown parser

    Returns:
        List of unique footnote IDs that are referenced (with the ^)
    """
    if markdown_parser is None:
        markdown_parser = flowmark_markdown(line_wrap_by_sentence(is_markdown=True))

    normalized_content = _normalize_footnotes_in_markdown(content)
    document = markdown_parser.parse(normalized_content)
    references: list[str] = []
    seen: set[str] = set()

    def collect_references(element: Any) -> None:
        if isinstance(element, footnote.FootnoteRef):
            footnote_id = f"^{element.label}"
            if footnote_id not in seen:
                seen.add(footnote_id)
                references.append(footnote_id)

    comprehensive_transform_tree(document, collect_references)
    return references
