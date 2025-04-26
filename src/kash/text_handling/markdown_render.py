from textwrap import dedent

import marko
import regex
from marko.block import HTMLBlock
from marko.ext.gfm import GFM
from marko.helpers import MarkoExtension


# When we use divs in Markdown we usually want them to be standalone paragraphs,
# so it doesn't break other wrapping with flowmark etc. This handles that.
class CustomHTMLBlockMixin:
    div_pattern = regex.compile(r"^\s*<div\b", regex.IGNORECASE)

    def render_html_block(self, element: HTMLBlock) -> str:
        stripped_body = element.body.strip()
        if self.div_pattern.match(stripped_body):
            return f"\n{stripped_body}\n"
        else:
            # marko attaches this to the superclass dynamically.
            return super().render_html_block(element)  # pyright: ignore


# GFM first, adding our custom override as an extension to handle divs our way.
# Extensions later in this list are earlier in MRO.
MARKO_GFM = marko.Markdown(extensions=[GFM, MarkoExtension(renderer_mixins=[CustomHTMLBlockMixin])])


def markdown_to_html(markdown: str, converter: marko.Markdown = MARKO_GFM) -> str:
    """
    Convert Markdown to HTML. Markdown may contain embedded HTML.
    """
    return converter.convert(markdown)


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
