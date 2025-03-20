import html
import re
from pathlib import Path

from inflect import engine
from prettyfmt import fmt_path

from kash.utils.common.lazyobject import lazyobject
from kash.utils.common.url import Locator, is_url


def plaintext_to_html(text: str):
    """
    Convert plaintext to HTML, also handling newlines and whitespace.
    """
    return (
        html.escape(text)
        .replace("\n", "<br>")
        .replace("\t", "&nbsp;" * 4)
        .replace("  ", "&nbsp;&nbsp;")
    )


def html_to_plaintext(text: str):
    """
    Convert HTML to plaintext, stripping tags and converting entities.
    """
    text = re.sub(r"<br>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<p>", "\n\n", text, flags=re.IGNORECASE)
    unescaped_text = html.unescape(text)
    clean_text = re.sub("<[^<]+?>", "", unescaped_text)
    return clean_text


def fmt_loc(locator: str | Locator, resolve: bool = True) -> str:
    """
    Use this to format URLs and paths. URLs are left unchanged.
    Paths are formatted in the standard way with `fmt_path`.
    """
    if isinstance(locator, Path):
        return fmt_path(locator, resolve=resolve)
    elif is_url(loc_str := str(locator)):
        return loc_str
    else:
        return fmt_path(locator, resolve=resolve)


@lazyobject
def inflect():
    return engine()


def fmt_count_items(count: int, name: str = "item") -> str:
    """
    Format a count and a name as a pluralized phrase, e.g. "1 item" or "2 items".
    """
    return f"{count} {inflect.plural(name, count)}"  # pyright: ignore


## Tests


def test_plaintext_to_html():
    assert plaintext_to_html("") == ""
    assert plaintext_to_html("Hello, World!") == "Hello, World!"
    assert plaintext_to_html("Hello\n  World!") == "Hello<br>&nbsp;&nbsp;World!"
    assert plaintext_to_html("Hello\tWorld!") == "Hello&nbsp;&nbsp;&nbsp;&nbsp;World!"
    assert plaintext_to_html("<Hello, World!>") == "&lt;Hello, World!&gt;"


def test_html_to_plaintext():
    assert html_to_plaintext("") == ""
    assert html_to_plaintext("<p>Hello, World!</p>") == "\n\nHello, World!"
    assert html_to_plaintext("<br>Hello, World!<br>") == "\nHello, World!\n"
    assert html_to_plaintext("<BR>Hello, World!<BR>") == "\nHello, World!\n"
    assert (
        html_to_plaintext(
            '<p>Hello,<br>World!<br><div>Hello, <span data-id="123">World!</span></div></p>'
        )
        == "\n\nHello,\nWorld!\nHello, World!"
    )
