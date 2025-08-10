from __future__ import annotations

import re
from typing import Any

from kash.utils.text_handling.escape_html_tags import escape_html_tags

_single_tilde_pat = re.compile(r"(?<!~)~(?!~)")
_alt_tilde = "～"


def _fix_single_tilde(html: str) -> str:
    """
    Escape standalone ~ characters with spaces before/after to avoid
    misinterpretation by markdownify as strikethrough. Using ～ because it's
    hard to properly escape ~ in a way that markdownify will respect.
    """

    def replace_tilde(match: re.Match[str]) -> str:
        start = match.start()
        end = match.end()
        # Check for space before or after
        has_space_before = start > 0 and html[start - 1].isspace()
        has_space_after = end < len(html) and html[end].isspace()
        return _alt_tilde if has_space_before or has_space_after else "~"

    return _single_tilde_pat.sub(replace_tilde, html)


def markdownify_preprocess(html: str) -> str:
    """
    Preprocess HTML before passing it to markdownify.
    """
    return _fix_single_tilde(html)


# Good options for markdownify. Without setting sup_symbol and sub_symbol, that
# info is typically lost.
MARKDOWNIFY_OPTIONS: dict[str, Any] = {
    "sup_symbol": "<__sup>",
    "sub_symbol": "<__sub>",
    "escape_underscores": True,
    "escape_asterisks": True,
    "escape_misc": False,  # This suppresses gratuitous escaping of -, ., etc.
    "newline_style": "BACKSLASH",
}


def _escape_html_in_md(md_text: str, whitelist_tags: set[str] | None = None) -> str:
    """
    HTML tags originally escaped with entities can get parsed and appear unescaped
    in the Markdown so it usually makes sense to do a full escaping (except for our
    custom sup/sub tags).
    """
    # Output from markdownify (especially from docx or other conversions) should
    # not have any HTML tags except for the custom sup/sub tags we've added.
    return escape_html_tags(
        md_text,
        allow_bare_md_urls=True,
        whitelist_tags={"__sup", "__sub"} | (whitelist_tags or set()),
    )


def markdownify_postprocess(md_text: str) -> str:
    """
    Postprocess Markdown after markdownify has converted HTML to Markdown.
    """
    md_text = _escape_html_in_md(md_text)
    # We use our own custom tags for sup/sub to avoid possible conflicts with other
    # tags in a doc. But when done we should replace them with the standard ones.
    return (
        md_text.replace("<__sup>", "<sup>")
        .replace("</__sup>", "</sup>")
        .replace("<__sub>", "<sub>")
        .replace("</__sub>", "</sub>")
    )


def markdownify_custom(html: str) -> str:
    """
    Customized version of `markdownify_convert to be more robust than with default settings.
    """

    from markdownify import markdownify as markdownify_convert

    preprocessed_html = markdownify_preprocess(html)
    md_text = markdownify_convert(preprocessed_html, **MARKDOWNIFY_OPTIONS)
    return markdownify_postprocess(md_text)
