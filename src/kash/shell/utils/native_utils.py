"""
Platform-specific tools and utilities.
"""

import os
import shlex
import subprocess
import time
import urllib.parse
import webbrowser
from enum import Enum
from pathlib import Path

from flowmark import Wrap
from funlog import log_calls

from kash.config.logger import get_logger
from kash.config.text_styles import BAT_STYLE, BAT_THEME, COLOR_ERROR
from kash.shell.output.shell_output import cprint
from kash.shell.utils.sys_tool_deps import PLATFORM, Platform, SysTool, sys_tool_check
from kash.shell.utils.terminal_images import terminal_show_image
from kash.utils.common.format_utils import fmt_loc
from kash.utils.common.url import as_file_url, is_file_url, is_url
from kash.utils.errors import FileNotFound, SetupError
from kash.utils.file_utils.file_formats import is_full_html_page, read_partial_text
from kash.utils.file_utils.file_formats_model import file_format_info

log = get_logger(__name__)


def file_size_check(
    filename: str | Path, max_lines: int = 100, max_bytes: int = 50 * 1024
) -> tuple[int, int]:
    """
    Get the size and scan to get initial line count (up to max_lines) of a file.
    """
    filename = str(filename)
    file_size = os.path.getsize(filename)
    line_min = 0
    with open(filename, "rb") as f:
        for i, _line in enumerate(f):
            if i >= max_lines or f.tell() > max_bytes:
                break
            line_min += 1
    return file_size, line_min


def native_open(filename: str | Path):
    filename = str(filename)
    log.message("Opening file: %s", filename)
    if PLATFORM == Platform.Darwin:
        subprocess.run(["open", filename])
    elif PLATFORM == Platform.Linux:
        subprocess.run(["xdg-open", filename])
    elif PLATFORM == Platform.Windows:
        subprocess.run(["start", shlex.quote(filename)], shell=True)
    else:
        raise NotImplementedError("Unsupported platform")


def native_open_url(url_or_query: str):
    """
    Open a URL or query in the system's default browser.
    """
    log.message("Opening in browser: %s", url_or_query)
    if is_url(url_or_query):
        webbrowser.open(url_or_query)
    else:
        webbrowser.open(f"https://www.google.com/search?q={urllib.parse.quote(url_or_query)}")


class ViewMode(Enum):
    auto = "auto"
    console = "console"
    browser = "browser"
    native = "native"
    terminal_image = "terminal_image"


@log_calls(level="info")
def _detect_view_mode(file_or_url: str) -> ViewMode:
    # As a heuristic, we use the browser for URLs and for local files that are
    # clearly full HTML pages (since HTML fragments are fine on console).
    if is_url(file_or_url) and not is_file_url(file_or_url):
        return ViewMode.browser

    path = Path(file_or_url)
    if path.is_file():  # File or symlink.
        content = read_partial_text(path)
        if content and is_full_html_page(content):
            return ViewMode.browser

        info = file_format_info(path)
        log.info("File format detected: %s", info)

        if info.is_text:
            return ViewMode.console
        if info.is_image:
            log.info("Detected image file, will display in terminal")
            return ViewMode.terminal_image
        else:
            return ViewMode.native
    elif path.is_dir():
        return ViewMode.native
    else:
        raise FileNotFound(fmt_loc(file_or_url))


def view_file_native(
    file_or_url: str | Path,
    view_mode: ViewMode = ViewMode.auto,
):
    """
    Open a file or URL in the console or a native app. If `view_mode` is auto,
    automatically determine whether to use console, web browser, or the user's
    preferred native application. For images, also tries terminal-based image
    display.
    """
    file_or_url = str(file_or_url)
    path = None
    if not is_url(file_or_url):
        path = Path(file_or_url)
        if not path.exists():
            raise FileNotFound(fmt_loc(path))

    if view_mode == ViewMode.auto:
        view_mode = _detect_view_mode(file_or_url)

    if view_mode == ViewMode.browser:
        url = file_or_url if is_url(file_or_url) else as_file_url(file_or_url)
        log.message("Opening URL in browser: %s", url)
        webbrowser.open(url)
    elif view_mode == ViewMode.console and path:
        file_size, min_lines = file_size_check(path)
        view_file_console(path, use_pager=min_lines > 40 or file_size > 20 * 1024)
    elif view_mode == ViewMode.terminal_image and path:
        try:
            terminal_show_image(path)
        except SetupError as e:
            log.info("%s: %s", e, path)
            native_open(path)
    elif view_mode == ViewMode.native:
        native_open(file_or_url)
    else:
        raise ValueError(f"Don't know how to view: {view_mode}: {file_or_url}")


def tail_file(
    *paths: str | Path,
    follow: bool = False,
    max_lines: int = 10000,
    follow_max_lines: int = 100,
    pick_recent_secs: int = 60 * 60 * 24,
):
    """
    Tail one or more log files. Just a wrapper around tail, bat, and/or less,
    with colorization using bat if available.

    If follow is set, does `tail -f` to follow the file for real-time updates.

    Uses bat if available. Note bat doesn't have efficient seek functionality like
    `less +G` so we prefer to use bat with less. Use Ctrl-C to quit less (this is
    enabled with `less -K`).

    For `tail -f`, using less is a worse experience (for example, you can't
    press enter to scroll down a few lines to observe if something changes)
    so we don't use less in that case.

    If `pick_recent_secs` is > 0 and multiple files are given, will only tail
    files that have been modified in the last `pick_recent_secs` seconds (by
    default, 1 day).
    """
    if not paths:
        raise ValueError("No paths provided")

    if pick_recent_secs and len(paths) > 1:
        selected_paths = [
            p for p in paths if Path(p).stat().st_mtime > time.time() - pick_recent_secs
        ]
    else:
        selected_paths = paths

    quoted_paths = [shlex.quote(str(p)) for p in selected_paths]
    all_paths_str = " ".join(quoted_paths)

    if follow:
        max_lines = follow_max_lines

    sys_tool_check().require(SysTool.tail)
    sys_tool_check().warn_if_missing(SysTool.bat)

    if follow:
        if sys_tool_check().has(SysTool.bat):
            # Follow the file in real-time.
            command = (
                f"tail -{max_lines} -f {all_paths_str} | "
                f"bat --paging=never --color=always --style=plain --theme={BAT_THEME} -l log"
                # Works nicer without less in this case (doesn't clear the screen).
            )
        else:
            command = f"tail -f {all_paths_str}"
        cprint("Following file: `%s`", command, text_wrap=Wrap.NONE)
    else:
        sys_tool_check().require(SysTool.less)
        if sys_tool_check().has(SysTool.bat, SysTool.less):
            command = (
                f"tail -{max_lines} {all_paths_str} | "
                f"bat --paging=never --color=always --style=plain --theme={BAT_THEME} -l log | "
                "less -K -R +G"
            )
        else:
            command = f"less +G {all_paths_str}"
        cprint("Tailing file: `%s`", command, text_wrap=Wrap.NONE)

    subprocess.run(command, shell=True, check=True)


def view_file_console(filename: str | Path, use_pager: bool = True):
    """
    Displays a file in the console with pagination and syntax highlighting.
    """
    filename = str(filename)
    quoted_filename = shlex.quote(filename)

    # TODO: Visualize YAML frontmatter with different syntax/style than Markdown content.

    is_text = file_format_info(filename).is_text
    if is_text:
        sys_tool_check().require(SysTool.less)
        if sys_tool_check().has(SysTool.bat):
            pager_str = "--pager=always --pager=less " if use_pager else ""
            command = f"bat {pager_str}--color=always --style={BAT_STYLE} --theme={BAT_THEME} {quoted_filename}"
        else:
            sys_tool_check().require(SysTool.pygmentize)
            command = f"pygmentize -g {quoted_filename}"
            if use_pager:
                command = f"{command} | less -R"
    else:
        sys_tool_check().require(SysTool.hexyl)
        command = f"hexyl {quoted_filename}"
        if use_pager:
            command = f"{command} | less -R"

    try:
        subprocess.run(command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        cprint(f"Error displaying file: {e}", style=COLOR_ERROR, text_wrap=Wrap.NONE)


def edit_files(*filenames: str | Path):
    """
    Edit a file using the user's preferred editor.
    """
    from kash.config.settings import global_settings

    editor = os.getenv("EDITOR", global_settings().default_editor)
    subprocess.run([editor] + list(filenames))


def native_trash(*paths: str | Path):
    from send2trash import send2trash

    send2trash(list(Path(p) for p in paths))
