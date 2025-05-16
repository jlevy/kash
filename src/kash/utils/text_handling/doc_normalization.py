from pathlib import Path

from flowmark import fill_markdown, line_wrap_by_sentence
from frontmatter_format import fmf_read, fmf_write

from kash.utils.common.format_utils import fmt_loc
from kash.utils.common.type_utils import not_none
from kash.utils.file_utils.file_formats_model import Format, detect_file_format
from kash.utils.rich_custom.ansi_cell_len import ansi_cell_len


def normalize_formatting(
    text: str,
    format: Format | None,
    support_ansi: bool = True,
    cleanups: bool = True,
) -> str:
    """
    Normalize formatting. Currently only normalizes Markdown and leaves plaintext
    and HTML intact.

    This only does "safe" normalizations that cannot break the text.
    Enables ANSI support so ANSI codes and OSC-8 links are correctly handled.
    """
    len_fn = ansi_cell_len if support_ansi else len
    if format == Format.markdown or format == Format.md_html:
        return fill_markdown(
            text,
            line_wrapper=line_wrap_by_sentence(len_fn=len_fn, is_markdown=True),
            cleanups=cleanups,
        )
    elif format == Format.plaintext:
        # Consider plaintext a raw format and don't normalize.
        # We could add support for formatted plaintext as well?
        # Then do: fill_text(text, width=width, word_splitter=simple_word_splitter, len_fn=len_fn)
        return text
    elif format == Format.html:
        # We don't currently auto-format HTML as we sometimes use HTML with specifically chosen line breaks.
        return text
    else:
        return text


def normalize_text_file(
    path: str | Path,
    target_path: Path,
    format: Format | None = None,
    support_ansi: bool = True,
) -> None:
    """
    Normalize formatting on a text file, handling Markdown, HTML, or text, as well as
    frontmatter, if present. `target_path` may be the same as `path`.
    """

    format = format or detect_file_format(path)
    if not format or not format.is_text:
        raise ValueError(f"Cannot format non-text files: {fmt_loc(path)}")

    content, metadata = fmf_read(path)
    norm_content = normalize_formatting(content, format=format, support_ansi=support_ansi)
    fmf_write(not_none(target_path), norm_content, metadata)


## Tests


def test_osc8_link():
    from clideps.terminal.osc_utils import osc8_link
    from flowmark.text_wrapping import wrap_paragraph

    link = osc8_link("https://example.com/" + "x" * 50, "Example")
    assert ansi_cell_len(link) == 7
    text = (link + " ") * 50
    wrapped = wrap_paragraph(text, width=80, len_fn=ansi_cell_len).splitlines()
    print([ansi_cell_len(line) for line in wrapped])
    print([len(line) for line in wrapped])
    assert all(ansi_cell_len(line) <= 80 for line in wrapped)
    assert all(len(line) >= 800 for line in wrapped)
