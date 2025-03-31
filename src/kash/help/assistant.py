import json
from collections.abc import Callable
from enum import Enum
from functools import cache

from flowmark import Wrap, fill_markdown
from funlog import log_calls
from pydantic import ValidationError
from rich.text import Text

from kash.config.logger import get_logger, record_console
from kash.config.settings import global_settings
from kash.config.text_styles import EMOJI_ASSISTANT, EMOJI_WARN, STYLE_ASSISTANCE, STYLE_HINT
from kash.docs.all_docs import DocSelection, all_docs
from kash.exec_model.script_model import Script
from kash.help.assistant_instructions import assistant_instructions
from kash.help.assistant_output import print_assistant_response
from kash.llm_utils import LLMCompletionResult, LLMDefault, LLMName, Message, llm_completion
from kash.model.assistant_response_model import AssistantResponse
from kash.model.items_model import Item, ItemType
from kash.shell.output.shell_output import PrintHooks, cprint, print_assistance, print_markdown
from kash.utils.common.format_utils import fmt_loc
from kash.utils.common.parse_shell_args import shell_unquote
from kash.utils.errors import InvalidState, KashRuntimeError, NoMatch
from kash.utils.file_formats.chat_format import (
    ChatHistory,
    ChatMessage,
    ChatRole,
    append_chat_message,
    tail_chat_history,
)
from kash.utils.file_utils.file_formats_model import Format
from kash.utils.lang_utils.capitalization import capitalize_cms
from kash.workspaces import current_ws

log = get_logger(__name__)


class AssistanceType(Enum):
    """
    Types of assistance offered, based on the model.
    """

    careful = LLMDefault.careful
    structured = LLMDefault.structured
    standard = LLMDefault.standard
    fast = LLMDefault.fast

    @property
    def workspace_llm(self) -> LLMName:
        return self.value.workspace_llm

    @property
    def is_structured(self) -> bool:
        return self == AssistanceType.structured

    @property
    def doc_selection(self) -> DocSelection:
        if self == AssistanceType.fast:
            return DocSelection.basic
        else:
            return DocSelection.full


@cache
def assist_preamble(is_structured: bool, doc_selection: DocSelection) -> str:
    # FIXME: Need to support various sizes of preamble without the full manual
    # as the current one is too large for quick help.
    from kash.help.help_pages import print_manual  # Avoid circular imports.

    with record_console() as console:
        cprint(str(assistant_instructions(is_structured)))
        print_manual(doc_selection)
        if doc_selection.value.api_docs:
            cprint(all_docs.api_docs, text_wrap=Wrap.NONE)

    preamble = console.export_text()
    log.info("Assistant preamble: %s chars (%s lines)", len(preamble), preamble.count("\n"))
    return preamble


def _insert_output(func: Callable, name: str) -> str:
    with record_console() as console:
        try:
            func()
        except (KashRuntimeError, ValueError, FileNotFoundError) as e:
            log.info("Skipping assistant input for %s: %s", name, e)
            output = f"(No {name} available)"

    output = console.export_text()
    log.info("Including %s lines of output to assistant for %s", output.count("\n"), name)

    return f"(output from the command `{name}`:)\n\n{output}"


@log_calls(level="warning", if_slower_than=0.5)
def assist_current_state() -> Message:
    from kash.commands.workspace.workspace_commands import (
        applicable_actions,
        files,
        history,
        select,
    )  # Avoid circular imports.

    ws = current_ws()
    ws_base_dir = ws.base_dir
    is_global_ws = ws.is_global_ws

    if ws_base_dir and not is_global_ws:
        ws_info = f"Based on the current directory, the current workspace is: {ws_base_dir.name} at {fmt_loc(ws_base_dir)}"
    else:
        if is_global_ws:
            about_ws = "You are currently using the `global` workspace."
        else:
            about_ws = "The current directory is not a workspace."
        ws_info = (
            f"{about_ws}. Create or switch to a workspace with the `workspace` command."
            "For example: `workspace my_new_workspace`."
        )

    log.info("Assistant current workspace state: %s", ws_info)

    # FIXME: Add @-mentioned files into context.

    current_state_message = Message(
        f"""
        ## Current State

        {ws_info}

        The last few commands issued by the user are:

        {_insert_output(lambda: history(max=30), "history")}

        The user's current selection is below:

        {_insert_output(select, "selection")}

        The actions with preconditions that match this selection, so are available to run on the
        current selection, are below:

        {_insert_output(applicable_actions, "applicable_actions")}

        And here is an overview of the files in the current directory:

        {_insert_output(lambda: files(overview=True), "files --overview")}
        """
    )
    log.info(
        "Assistant current state message: %s chars (%s lines)",
        len(current_state_message),
        current_state_message.count("\n"),
    )
    return current_state_message


@log_calls(level="info")
def assist_system_message_with_state(
    is_structured: bool,
    doc_selection: DocSelection,
) -> Message:
    return Message(
        f"""
        {assist_preamble(is_structured=is_structured, doc_selection=doc_selection)}

        {assist_current_state()}
        """
        # TODO: Include selection history, command history, any other info about files in the workspace.
    )


def assistant_chat_history(
    include_system_message: bool,
    is_structured: bool,
    doc_selection: DocSelection,
    max_records: int = 20,
) -> ChatHistory:
    ws = current_ws()
    history_path = ws.base_dir / ws.dirs.assistant_history_yml

    assistant_history = ChatHistory()
    try:
        assistant_history = tail_chat_history(history_path, max_records=max_records)
    except FileNotFoundError:
        log.info("No assistant history file found: %s", history_path)
    except (InvalidState, ValueError) as e:
        log.warning("Couldn't load assistant history, so skipping it: %s", e)

    if include_system_message:
        system_message = assist_system_message_with_state(
            is_structured=is_structured, doc_selection=doc_selection
        )
        assistant_history.messages.insert(0, ChatMessage(ChatRole.system, system_message))

    return assistant_history


def append_assistant_history(user_message: ChatMessage, response_text: ChatMessage):
    ws = current_ws()
    history_path = ws.base_dir / ws.dirs.assistant_history_yml
    append_chat_message(history_path, user_message)
    append_chat_message(history_path, response_text)


def assistance_unstructured(messages: list[dict[str, str]], model: LLMName) -> LLMCompletionResult:
    """
    Get general assistance, with unstructured output.
    Must provide all context within the messages.
    """
    # TODO: Stream response.

    return llm_completion(
        model,
        messages=messages,
        save_objects=global_settings().debug_assistant,
    )


def assistance_structured(messages: list[dict[str, str]], model: LLMName) -> AssistantResponse:
    """
    Get general assistance, with unstructured or structured output.
    Must provide all context within the messages.
    """

    response = llm_completion(
        model,
        messages=messages,
        save_objects=global_settings().debug_assistant,
        response_format=AssistantResponse,
    )

    try:
        response_data = json.loads(response.content)
        assistant_response = AssistantResponse.model_validate(response_data)
        log.debug("Assistant response: %s", assistant_response)
    except (ValidationError, json.JSONDecodeError) as e:
        log.error("Error parsing assistant response: %s", e)
        raise e

    return assistant_response


def shell_context_assistance(
    input: str,
    silent: bool = False,
    model: LLMName | None = None,
    assistance_type: AssistanceType = AssistanceType.standard,
) -> None:
    """
    Get assistance, using the full context of the shell.
    """
    # For fast response, check for near-exact FAQ matches first.
    from kash.help.help_printing import print_explain_command

    try:
        print_explain_command(input, assistant_model=None)
        return
    except NoMatch:
        pass

    if not model:
        model = assistance_type.workspace_llm

    doc_selection = assistance_type.doc_selection
    if not silent:
        cprint(
            Text.assemble(
                (f"{EMOJI_ASSISTANT} Thinking… ", STYLE_ASSISTANCE),
                (f"({assistance_type.name}, {model}, {doc_selection})", STYLE_HINT),
            )
        )

    # Get shell chat history.

    history = assistant_chat_history(
        include_system_message=False,
        is_structured=assistance_type.is_structured,
        doc_selection=doc_selection,
    )

    # Insert the system message.
    system_message = assist_system_message_with_state(
        is_structured=assistance_type.is_structured,
        doc_selection=doc_selection,
    )
    history.messages.insert(0, ChatMessage(ChatRole.system, system_message))

    # Record the user's message.
    input = shell_unquote(input)
    log.info("User request to assistant: %s", input)
    user_message = ChatMessage(ChatRole.user, input)
    history.append(user_message)
    log.info("Assistant history context (including new message): %s", history.size_summary())

    # Get the assistant's response.
    if assistance_type.is_structured:
        assistant_response = assistance_structured(history.as_chat_completion(), model)

        # Save the user message to the history after a response. That way if the
        # use changes their mind right away and cancels it's not left in the file.
        append_assistant_history(
            user_message, ChatMessage(ChatRole.assistant, assistant_response.model_dump())
        )

        PrintHooks.before_assistance()
        print_assistant_response(assistant_response, model, doc_selection)
        PrintHooks.after_assistance()

        # If the assistant suggests commands, also save them as a script.
        if assistant_response.suggested_commands:
            response_text = fill_markdown(assistant_response.response_text)

            script = Script(
                commands=list(assistant_response.suggested_commands),
                signature=None,  # TODO Infer from first command.
            )
            item = Item(
                type=ItemType.script,
                title=f"Assistant Answer: {capitalize_cms(input)}",
                description=response_text,
                format=Format.kash_script,
                body=script.script_str,
            )
            ws = current_ws()
            ws.save(item, as_tmp=True)

    else:
        assistant_response = assistance_unstructured(history.as_chat_completion(), model)
        append_assistant_history(
            user_message, ChatMessage(ChatRole.assistant, assistant_response.content)
        )
        PrintHooks.before_assistance()
        print_markdown(assistant_response.content)
        PrintHooks.after_assistance()

    # FIXME: Make these obvious buttons.
    if assistance_type in (AssistanceType.fast, AssistanceType.standard):
        PrintHooks.spacer()
        print_assistance(
            f"{EMOJI_WARN} For more detailed assistance, use `assist --type=careful` or `assist --type=structured`."
        )
