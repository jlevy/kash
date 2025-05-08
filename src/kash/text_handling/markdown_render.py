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
        # Apply GFM filtering first via the next renderer in the MRO.
        filtered_body = super().render_html_block(element)  # pyright: ignore

        # Check if the original block was a div.
        if self.div_pattern.match(element.body.strip()):
            # If it was a div, wrap the *filtered* result in newlines.
            return f"\n{filtered_body.strip()}\n"
        else:
            # Otherwise, return the GFM-filtered body directly.
            return filtered_body


# GFM first, adding our custom override as an extension to handle divs our way.
# Extensions later in this list are earlier in MRO.
MARKO_GFM = marko.Markdown(
    extensions=["footnote", GFM, MarkoExtension(renderer_mixins=[CustomHTMLBlockMixin])]
)


FOOTNOTE_UP_ARROW = "&nbsp;↑&nbsp;"


def html_postprocess(html: str) -> str:
    """
    Final tweaks to the HTML.
    """
    # TODO: Improve rendering of footnote defs to put the up arrow next to the number instead?
    html = html.replace(
        """class="footnote">&#8617;</a>""", f"""class="footnote">{FOOTNOTE_UP_ARROW}</a>"""
    )
    return html


def markdown_to_html(markdown: str, converter: marko.Markdown = MARKO_GFM) -> str:
    """
    Convert Markdown to HTML.

    Wraps div blocks with newlines for better Markdown compatibility.

    Output passes through raw HTML! Note per GFM, unsafe script tags etc
    are [allowed in some cases](https://github.github.com/gfm/#example-140) so
    additional sanitization is needed if input isn't trusted.
    """
    html = converter.convert(markdown)
    return html_postprocess(html)
    return html


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

        <div class="div2">This is a second div.
        <iframe src="https://example.com">Inline iframe, note this is sanitized</iframe>
        </div>

        <!-- Script tag in a block, note this isn't sanitized -->
        <script>console.log("Javascript block!");</script>
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

        <div class="div2">This is a second div.
        &lt;iframe src="https://example.com">Inline iframe, note this is sanitized</iframe>
        </div>
        <!-- Script tag in a block, note this isn't sanitized -->
        <script>console.log("Javascript block!");</script>
        """
    )

    assert markdown_to_html(markdown).strip() == expected_html.strip()
