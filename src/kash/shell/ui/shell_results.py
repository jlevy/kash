from typing import Any

from rich.box import SQUARE
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from kash.config.logger import get_console, get_logger
from kash.config.text_styles import COLOR_SELECTION, STYLE_HINT
from kash.exec.command_exec import run_command_or_action
from kash.exec_model.shell_model import ShellResult
from kash.shell.output.shell_output import PrintHooks, console_pager, cprint, print_result
from kash.utils.common.format_utils import fmt_count_items, fmt_loc
from kash.utils.errors import is_fatal
from kash.workspaces import SelectionHistory

log = get_logger(__name__)

MAX_LINES_WITHOUT_PAGING = 128


def shell_print_selection_history(
    sh: SelectionHistory, last: int | None = None, after_cur: int | None = None
) -> None:
    """
    Print the current selection history. Shows back last items, and forward until
    the end of the list (or `after_cur` items forward if that is provided).
    """
    n = len(sh.history)
    start_idx = max(0, sh.current_index - last) if last else 0
    end_idx = min(n, sh.current_index + after_cur) if after_cur else n
    history_slice = sh.history[start_idx:end_idx]
    width = get_console().width

    if n == 0:
        content = Text("No selection history.", style=COLOR_SELECTION)
        panel_title = "Selection History"
        cprint(
            Panel(
                content,
                box=SQUARE,
                style=COLOR_SELECTION,
                padding=(0, 1),
                title=panel_title,
            ),
            width=width,
        )
    else:
        table = Table(show_header=False, box=None, pad_edge=False)
        for v, selection in enumerate(history_slice):
            i = v + start_idx
            is_current = i == sh.current_index
            box_color = COLOR_SELECTION if is_current else STYLE_HINT
            content_color = "default" if is_current else STYLE_HINT

            if not selection.paths:
                selection_text = Text("No selection.", style=content_color)
            else:
                selection_text = Text(
                    "\n".join(fmt_loc(p) for p in selection.paths), style=content_color
                )

            selection_title = (
                f"$selections[{-(n - i)}]: {fmt_count_items(len(selection.paths), 'item')}"
            )
            if is_current:
                selection_title = f"Current selection: {selection_title}"

            selection_panel = Panel(
                selection_text,
                box=SQUARE,
                padding=(0, 1),
                style=box_color,
                title=Text(selection_title, style=box_color),
                width=width,
            )
            table.add_row(selection_panel)

        cprint(table, width=width)

    # if n > 0:
    #     cprint("(history is in $selections)", style=COLOR_HINT)


def shell_print_result(value: Any | None) -> None:
    if value:
        if isinstance(value, list) and all(isinstance(item, str) for item in value):
            str_lines = "\n".join(value)
            if len(value) > MAX_LINES_WITHOUT_PAGING:
                with console_pager():
                    print_result(str_lines)
            else:
                print_result(str_lines)
        else:
            print_result(str(value))

        PrintHooks.after_result()


def show_shell_result(res: ShellResult) -> None:
    """
    Handle the result of a command, displaying output, selection, etc.
    """
    if res.exception:
        # Nonfatal exceptions will already be logged.
        if is_fatal(res.exception):
            raise res.exception

    if res.display_command:
        log.message("Displaying result with: %s", res.display_command)
        command_output = run_command_or_action(res.display_command)
        if command_output:
            log.info("Ignoring display command output: %s", command_output)

    if res.result and res.show_result:
        PrintHooks.before_result()
        shell_print_result(res.result)
        cprint(f"({fmt_count_items(len(res.result), 'item')} in $result)", style=STYLE_HINT)
