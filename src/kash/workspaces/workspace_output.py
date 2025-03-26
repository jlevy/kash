from pathlib import Path

from chopdiff.divs.parse_divs import parse_divs
from flowmark import Wrap
from frontmatter_format import fmf_read, fmf_read_frontmatter_raw
from prettyfmt import fmt_size_dual
from rich.box import SQUARE
from rich.panel import Panel
from rich.text import Text

from kash.config.logger import get_console, get_logger
from kash.config.text_styles import COLOR_SELECTION
from kash.exec_model.shell_model import ShellResult
from kash.model.items_model import ItemType
from kash.shell.output.kerm_code_utils import click_to_paste
from kash.shell.output.shell_output import PrintHooks, cprint, format_name_and_value
from kash.utils.common.format_utils import fmt_count_items, fmt_loc
from kash.utils.file_formats.chat_format import ChatHistory
from kash.utils.file_utils.dir_size import get_dir_size
from kash.utils.file_utils.file_formats_model import file_format_info
from kash.workspaces import Selection, current_ws

log = get_logger(__name__)


def shell_print_selection(selection: Selection) -> None:
    """
    Print the current selection.
    """
    if not selection.paths:
        content = Text("No selection.", style="default")
    else:
        content = Text("\n").join(click_to_paste(fmt_loc(p)) for p in selection.paths)

    panel_title = f"Current selection: {fmt_count_items(len(selection.paths), 'item')}"
    width = get_console().width

    cprint(
        Panel(
            content,
            box=SQUARE,
            style=COLOR_SELECTION,
            padding=(0, 1),
            title=Text(panel_title, style=COLOR_SELECTION),
            title_align="left",
        ),
        width=width,
    )

    # if selection.paths:
    #     cprint("(in $selection)", style=COLOR_HINT)


def post_shell_result(res: ShellResult) -> None:
    if res.show_selection or res.suggest_actions:
        selection = current_ws().selections.current

        if res.show_selection:
            PrintHooks.before_show_selection()
            shell_print_selection(selection)

        if selection and res.suggest_actions:
            from kash.commands.workspace.workspace_commands import suggest_actions

            PrintHooks.before_suggest_actions()
            suggest_actions()


def print_dir_info(path: Path, text_wrap: Wrap = Wrap.NONE):
    dir_info = get_dir_size(path)

    cprint(format_name_and_value("total files", f"{dir_info.file_count}"), text_wrap=text_wrap)
    cprint(
        format_name_and_value("total size", fmt_size_dual(dir_info.total_size)), text_wrap=text_wrap
    )


def print_file_info(
    input_path: Path,
    show_size_details: bool = False,
    show_format: bool = False,
    text_wrap: Wrap = Wrap.NONE,
):
    if input_path.is_dir():
        print_dir_info(input_path, text_wrap)
        return

    # Format info.
    detected_format = None
    if show_format:
        format_info = file_format_info(input_path)
        cprint(format_name_and_value("format", format_info.as_str()), text_wrap=text_wrap)
        detected_format = format_info.format

    # Size info.
    size = Path(input_path).stat().st_size
    cprint(format_name_and_value("size", fmt_size_dual(size)), text_wrap=text_wrap)

    # Raw frontmatter info.
    try:
        _frontmatter_str, offset, _ = fmf_read_frontmatter_raw(input_path)
    except UnicodeDecodeError:
        offset = None

    # Structured frontmatter and content info.
    body = None
    if show_size_details and detected_format and detected_format.supports_frontmatter:
        try:
            body, frontmatter = fmf_read(input_path)

            item_type = None
            if frontmatter:
                if offset:
                    cprint(
                        format_name_and_value(
                            "frontmatter",
                            f"{len(frontmatter)} keys, {fmt_size_dual(offset)}",
                        ),
                        text_wrap=text_wrap,
                    )
                item_type = frontmatter.get("type")
                if item_type:
                    cprint(
                        format_name_and_value("item type", item_type),
                        text_wrap=text_wrap,
                    )
            if body:
                # Show chat history info.
                if item_type and item_type == ItemType.chat.value:
                    try:
                        chat_history = ChatHistory.from_yaml(body)
                        size_summary_str = chat_history.size_summary()
                        cprint(
                            format_name_and_value("chat history", size_summary_str),
                            text_wrap=text_wrap,
                        )
                    except Exception:
                        pass
                # Parse text body.
                parsed_body = parse_divs(body)
                size_summary_str = parsed_body.size_summary()
                cprint(
                    format_name_and_value("body", size_summary_str),
                    text_wrap=Wrap.NONE,
                )
        except UnicodeDecodeError as e:
            log.warning("Error reading content as text, skipping body: %s", e)

    else:
        if offset:
            cprint(
                format_name_and_value("frontmatter", fmt_size_dual(offset)),
                text_wrap=text_wrap,
            )
