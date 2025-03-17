from textwrap import dedent
from typing import Any

import marko
import regex
from marko.block import Heading, HTMLBlock, ListItem
from marko.inline import Link

from kash.config.logger import get_logger

log = get_logger(__name__)


def as_bullet_points(values: list[str]) -> str:
    """
    Convert a list of strings to a Markdown bullet-point list.
    """
    return "\n\n".join([f"- {point}" for point in values])


class CustomHTMLRenderer(marko.HTMLRenderer):
    """
    When wrapping paragraphs as divs in Markdown we usually want them to be paragraphs.
    This handles that.
    """

    div_pattern = regex.compile(r"^\s*<div\b", regex.IGNORECASE)

    def render_html_block(self, element: HTMLBlock) -> str:
        if self.div_pattern.match(element.body.strip()):
            return f"\n{element.body.strip()}\n"
        else:
            return element.body


standard_markdown = marko.Markdown()

custom_markdown = marko.Markdown(renderer=CustomHTMLRenderer)


def markdown_to_html(markdown: str, converter: marko.Markdown = custom_markdown) -> str:
    """
    Convert Markdown to HTML. Markdown may contain embedded HTML.
    """
    return converter.convert(markdown)


def is_markdown_header(markdown: str) -> bool:
    """
    Is the start of this content a Markdown header?
    """
    return regex.match(r"^#+ ", markdown) is not None


def _tree_links(element, include_internal=False):
    links = []

    def _find_links(element):
        match element:
            case Link():
                if include_internal or not element.dest.startswith("#"):
                    links.append(element.dest)
            case _:
                if hasattr(element, "children"):
                    for child in element.children:
                        _find_links(child)

    _find_links(element)
    return links


def extract_links(file_path: str, include_internal=False) -> list[str]:
    """
    Extract all links from a Markdown file. Future: Include textual and section context.
    """

    with open(file_path) as file:
        content = file.read()
        document = marko.parse(content)
        return _tree_links(document, include_internal)


def _extract_text(element: Any) -> str:
    if isinstance(element, str):
        return element
    elif hasattr(element, "children"):
        return "".join(_extract_text(child) for child in element.children)
    else:
        return ""


def _tree_bullet_points(element: marko.block.Document) -> list[str]:
    bullet_points: list[str] = []

    def _find_bullet_points(element):
        if isinstance(element, ListItem):
            bullet_points.append(_extract_text(element).strip())
        elif hasattr(element, "children"):
            for child in element.children:
                _find_bullet_points(child)

    _find_bullet_points(element)
    return bullet_points


def extract_bullet_points(content: str) -> list[str]:
    """
    Extract list item values from a Markdown file.
    """

    document = marko.parse(content)
    return _tree_bullet_points(document)


def _type_from_heading(heading: Heading) -> str:
    if heading.level in [1, 2, 3, 4, 5, 6]:
        return f"h{heading.level}"
    else:
        raise ValueError(f"Unsupported heading: {heading}: level {heading.level}")


## Tests


def test_markdown_to_html():
    markdown = dedent(
        """
        # Heading

        This is a paragraph and a [link](https://example.com).

        - Item 1
        - Item 2

        ## Subheading

        This is a paragraph with a <span>span</span> tag.
        This is a paragraph with a <div>div</div> tag.
        This is a paragraph with an <a href='https://example.com'>example link</a>.

        <div class="div1">This is a div.</div>

        <div class="div2">This is a second div.</div>
        """
    )
    print(markdown_to_html(markdown))

    expected_html = dedent(
        """
        <h1>Heading</h1>
        <p>This is a paragraph and a <a href="https://example.com">link</a>.</p>
        <ul>
        <li>Item 1</li>
        <li>Item 2</li>
        </ul>
        <h2>Subheading</h2>
        <p>This is a paragraph with a <span>span</span> tag.
        This is a paragraph with a <div>div</div> tag.
        This is a paragraph with an <a href='https://example.com'>example link</a>.</p>

        <div class="div1">This is a div.</div>

        <div class="div2">This is a second div.</div>
        """
    )

    assert markdown_to_html(markdown).strip() == expected_html.strip()
