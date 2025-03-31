import os

from frontmatter_format import fmf_read_raw, fmf_strip_frontmatter
from prettyfmt import fmt_lines
from strif import copyfile_atomic

from kash.config.logger import get_logger
from kash.config.text_styles import STYLE_EMPH
from kash.exec import assemble_path_args, kash_command, resolve_path_arg
from kash.shell.output.shell_output import (
    PadStyle,
    PrintHooks,
    Wrap,
    cprint,
    print_status,
    print_style,
)
from kash.shell.utils.native_utils import edit_files, native_trash
from kash.shell.utils.native_utils import tail_file as native_tail_file
from kash.utils.common.format_utils import fmt_loc
from kash.utils.errors import InvalidInput
from kash.utils.file_utils.file_formats_model import detect_file_format
from kash.workspaces.workspace_output import print_file_info

log = get_logger(__name__)


@kash_command
def cbcopy(path: str | None = None, raw: bool = False) -> None:
    """
    Copy the contents of a file (or the first file in the selection) to the OS-native
    clipboard.

    :param raw: Copy the full exact contents of the file. Otherwise frontmatter is omitted.
    """
    # TODO: Get this to work for images!
    import pyperclip

    input_paths = assemble_path_args(path)
    input_path = input_paths[0]

    format = detect_file_format(input_path)
    if not format or not format.is_text:
        raise InvalidInput(f"Cannot copy non-text files to clipboard: {fmt_loc(input_path)}")

    if raw:
        with open(input_path) as f:
            content = f.read()

        pyperclip.copy(content)
        print_status(
            "Copied raw contents of file to clipboard (%s chars):\n%s",
            len(content),
            fmt_lines([fmt_loc(input_path)]),
        )
    else:
        content, metadata_str = fmf_read_raw(input_path)
        pyperclip.copy(content)
        skip_msg = ""
        if metadata_str:
            skip_msg = f", skipping {len(metadata_str)} chars of frontmatter"
        print_status(
            "Copied contents of file to clipboard (%s chars%s):\n%s",
            len(content),
            skip_msg,
            fmt_lines([fmt_loc(input_path)]),
        )


@kash_command
def edit(path: str | None = None, all: bool = False) -> None:
    """
    Edit the contents of a file using the user's default editor (or defaulting to nano).

    :param all: Normally edits only the first file given. This passes all files to the editor.
    """
    input_paths = assemble_path_args(path)
    if not all:
        input_paths = [input_paths[0]]

    edit_files(*input_paths)


@kash_command
def file_info(*paths: str, size_summary: bool = False, format: bool = False) -> None:
    """
    Show info about a file. By default this includes a summary of the size and HTML
    structure of the items at the given paths (for text documents) and the detected
    mime type.

    :param size_summary: Only show size summary (words, sentences, paragraphs for a text document).
    :param format: Only show detected file format.
    """
    if not size_summary and not format:
        size_summary = format = True

    # FIXME: Ensure this yields absolute paths for global workspace store paths
    input_paths = assemble_path_args(*paths)
    for input_path in input_paths:
        cprint(f"{fmt_loc(input_path)}:", style=STYLE_EMPH, text_wrap=Wrap.NONE)
        with print_style(PadStyle.INDENT):
            print_file_info(input_path, show_size_details=size_summary, show_format=format)
        PrintHooks.spacer()


@kash_command
def rename(path: str, new_path: str) -> None:
    """
    Rename a file or item. Creates any new parent paths as needed.
    Note this may invalidate relations that point to the old store path.

    TODO: Add an option here to update all relations in the workspace.
    """
    from_path, to_path = assemble_path_args(path, new_path)
    to_path.parent.mkdir(parents=True, exist_ok=True)
    os.rename(from_path, to_path)

    print_status(f"Renamed: {fmt_loc(from_path)} -> {fmt_loc(to_path)}")


@kash_command
def copy(*paths: str) -> None:
    """
    Copy the items at the given paths to the target path.
    """
    if len(paths) < 2:
        raise InvalidInput("Must provide at least one source path and a target path")

    src_paths = [resolve_path_arg(path) for path in paths[:-1] if path]
    dest_path = resolve_path_arg(paths[-1])

    if len(src_paths) == 1 and dest_path.is_dir():
        dest_path = dest_path / src_paths[0].name
    elif len(src_paths) > 1 and not dest_path.is_dir():
        raise InvalidInput(f"Cannot copy multiple files to a file target: {dest_path}")

    for src_path in src_paths:
        copyfile_atomic(src_path, dest_path, make_parents=True)

    print_status(
        f"Copied:\n{fmt_lines(fmt_loc(p) for p in src_paths)}\n->\n{fmt_lines([fmt_loc(dest_path)])}",
    )


@kash_command
def trash(*paths: str) -> None:
    """
    Trash the items at the given paths. Uses OS-native trash or recycle bin on Mac, Windows, or Linux.
    """

    resolved_paths = assemble_path_args(*paths)
    native_trash(*resolved_paths)
    print_status(f"Deleted (check trash or recycling bin to recover):\n{fmt_lines(resolved_paths)}")


@kash_command
def strip_frontmatter(*paths: str) -> None:
    """
    Strip the frontmatter from the given files.
    """
    input_paths = assemble_path_args(*paths)

    for path in input_paths:
        log.message("Stripping frontmatter from: %s", fmt_loc(path))
        fmf_strip_frontmatter(path)


@kash_command
def tail_file(*paths: str, follow: bool = False) -> None:
    """
    Tail one or more files. With colorization using bat if available, otherwise
    using less. If `follow` is True, follows the file as it grows.
    """

    native_tail_file(*paths, follow=follow)


@kash_command
def follow_file(*paths: str) -> None:
    """
    Same as `tail_file --follow`.
    """
    native_tail_file(*paths, follow=True)
