from pathlib import Path

from flowmark import fill_markdown, fill_text, line_wrap_by_sentence
from flowmark.text_filling import DEFAULT_WRAP_WIDTH
from flowmark.text_wrapping import simple_word_splitter, wrap_paragraph
from frontmatter_format import fmf_read, fmf_write

from kash.utils.common.format_utils import fmt_loc
from kash.utils.common.type_utils import not_none
from kash.utils.file_utils.file_formats_model import Format, detect_file_format
from kash.utils.rich_custom.ansi_cell_len import ansi_cell_len


def normalize_formatting_ansi(text: str, format: Format | None, width=DEFAULT_WRAP_WIDTH) -> str:
    """
    Normalize text formatting by wrapping lines and normalizing Markdown.
    Enables ANSI support so ANSI codes and OSC-8 links are correctly handled.
    """
    if format == Format.plaintext:
        return fill_text(
            text, width=width, word_splitter=simple_word_splitter, len_fn=ansi_cell_len
        )
    elif format == Format.markdown or format == Format.md_html:
        return fill_markdown(text, line_wrapper=line_wrap_by_sentence(len_fn=ansi_cell_len))
    elif format == Format.html:
        # We don't currently auto-format HTML as we sometimes use HTML with specifically chosen line breaks.
        return text
    else:
        return text


def normalize_text_file(
    path: str | Path,
    target_path: Path,
    format: Format | None = None,
) -> None:
    """
    Normalize formatting on a text file, handling Markdown, HTML, or text, as well as
    frontmatter, if present. `target_path` may be the same as `path`.
    """

    format = format or detect_file_format(path)
    if not format or not format.is_text:
        raise ValueError(f"Cannot format non-text files: {fmt_loc(path)}")

    content, metadata = fmf_read(path)
    norm_content = normalize_formatting_ansi(content, format=format)
    fmf_write(not_none(target_path), norm_content, metadata)


## Tests


def test_osc8_link():
    from kash.shell.utils.osc_utils import osc8_link

    link = osc8_link("https://example.com/" + "x" * 50, "Example")
    assert ansi_cell_len(link) == 7
    text = (link + " ") * 50
    wrapped = wrap_paragraph(text, width=80, len_fn=ansi_cell_len).splitlines()
    print([ansi_cell_len(line) for line in wrapped])
    print([len(line) for line in wrapped])
    assert all(ansi_cell_len(line) <= 80 for line in wrapped)
    assert all(len(line) >= 800 for line in wrapped)
