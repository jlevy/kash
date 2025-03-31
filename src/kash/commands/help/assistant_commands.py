from rich import get_console

from kash.commands.base.basic_file_commands import trash
from kash.commands.workspace.selection_commands import select
from kash.config.logger import get_logger
from kash.config.text_styles import PROMPT_ASSIST, SPINNER
from kash.docs.all_docs import DocSelection
from kash.exec import kash_command
from kash.exec_model.shell_model import ShellResult
from kash.help.assistant import (
    AssistanceType,
    assist_system_message_with_state,
    shell_context_assistance,
)
from kash.llm_utils import LLM
from kash.model.items_model import Item, ItemType
from kash.shell.input.input_prompts import input_simple_string
from kash.shell.utils.native_utils import tail_file
from kash.utils.file_utils.file_formats_model import Format
from kash.workspaces import current_ws

log = get_logger(__name__)


@kash_command
def assist(
    input: str | None = None,
    model: LLM | None = None,
    type: AssistanceType = AssistanceType.standard,
) -> None:
    """
    Invoke the kash assistant. You don't normally need this command as it is the same as just
    asking a question (a question ending with ?) on the kash console.

    :param type: The type of assistance to use.
    :param model: The model to use for the assistant. If not provided, the default model
        for the assistant type is used.
    """
    if not input:
        input = input_simple_string(
            "What do you need help with? (Ask any question or press enter to see main `help` page.)",
            prompt_symbol=PROMPT_ASSIST,
        )
        if not input or not input.strip():
            help()
            return

    with get_console().status("Thinking…", spinner=SPINNER):
        shell_context_assistance(input, model=model, assistance_type=type)


@kash_command
def assistant_system_message(
    is_structured: bool = False,
    doc_selection: DocSelection = DocSelection.full,
) -> ShellResult:
    """
    Save the assistant system message. Useful for debugging.
    """

    item = Item(
        type=ItemType.export,
        title="Assistant System Message",
        format=Format.markdown,
        body=assist_system_message_with_state(
            is_structured=is_structured,
            doc_selection=doc_selection,
        ),
    )
    ws = current_ws()
    store_path = ws.save(item, as_tmp=True)

    log.message("Saved assistant system message to %s", store_path)

    select(store_path)

    return ShellResult(show_selection=True)


@kash_command
def assistant_history(follow: bool = False) -> None:
    """
    Show the assistant history for the current workspace.

    :param follow: Follow the file as it grows.
    """
    ws = current_ws()
    tail_file(ws.base_dir / ws.dirs.assistant_history_yml, follow=follow)


@kash_command
def clear_assistant() -> None:
    """
    Clear the assistant history for the current workspace. Old history file will be
    moved to the trash.
    """
    ws = current_ws()
    path = ws.base_dir / ws.dirs.assistant_history_yml
    if path.exists():
        trash(path)
