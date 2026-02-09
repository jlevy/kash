from __future__ import annotations

import re
from dataclasses import dataclass

from prompt_toolkit import search
from prompt_toolkit.application import get_app
from prompt_toolkit.filters import Condition
from prompt_toolkit.key_binding import KeyBindings, merge_key_bindings
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.shortcuts import print_formatted_text
from strif import AtomicVar
from xonsh.parsers.completion_context import CommandContext

from kash.actions.core.assistant_chat import assistant_chat
from kash.config.logger import get_logger
from kash.shell.completions.completion_types import ScoredCompletion
from kash.shell.completions.shell_completions import (
    trace_completions,
)
from kash.shell.ui.shell_syntax import assist_request_str
from kash.xonsh_custom.shell_which import is_valid_command

log = get_logger(__name__)


@dataclass
class MultiTabState:
    last_context: CommandContext | None = None
    first_results_shown: bool = False
    more_results_requested: bool = False
    more_completions: set[ScoredCompletion] | None = None

    def reset_first_results(self, context: CommandContext):
        self.last_context = context
        self.first_results_shown = True
        self.more_results_requested = False
        self.more_completions = None

    def could_show_more(self) -> bool:
        return self.first_results_shown and not self.more_results_requested


# Maintain state for help completions for single and double tab.
# TODO: Move this into the CompletionContext.
_MULTI_TAB_STATE = AtomicVar(MultiTabState())


@Condition
def is_unquoted_assist_request():
    app = get_app()
    buf = app.current_buffer
    text = buf.text.strip()
    is_default_buffer = buf.name == "DEFAULT_BUFFER"
    has_prefix = text.startswith("?") and not (text.startswith('? "') or text.startswith("? '"))
    return is_default_buffer and has_prefix


_command_regex = re.compile(r"^[a-zA-Z0-9_-]+$")

_python_keyword_regex = re.compile(
    r"assert|async|await|break|class|continue|def|del|elif|else|except|finally|"
    r"for|from|global|if|import|lambda|nonlocal|pass|raise|return|try|while|with|yield"
)


def _extract_command_name(text: str) -> str | None:
    text = text.split()[0]
    if _python_keyword_regex.match(text):
        return None
    if _command_regex.match(text):
        return text
    return None


@Condition
def whitespace_only() -> bool:
    app = get_app()
    buf = app.current_buffer
    return not buf.text.strip()


@Condition
def is_typo_command() -> bool:
    """
    Is the command itself invalid? Should be conservative, so we can suppress
    executing it if it is definitely a typo.
    """

    app = get_app()
    buf = app.current_buffer
    text = buf.text.strip()

    is_default_buffer = buf.name == "DEFAULT_BUFFER"
    if not is_default_buffer:
        return False

    # Assistant NL requests always allowed.
    has_assistant_prefix = text.startswith("?") or text.rstrip().endswith("?")
    if has_assistant_prefix:
        return False

    # Anything more complex is probably Python.
    # TODO: Do a better syntax parse of this as Python, or use xonsh's algorithm.
    for s in ["\n", "(", ")"]:
        if s in text:
            return False

    # Empty command line allowed.
    if not text:
        return False

    # Now look at the command.
    command_name = _extract_command_name(text)

    # Python or missing command is fine.
    if not command_name:
        return False

    # Recognized command.
    if is_valid_command(command_name):
        return False

    # Okay it's almost certainly a command typo.
    return True


@Condition
def is_completion_menu_active() -> bool:
    app = get_app()
    return app.current_buffer.complete_state is not None


@Condition
def could_show_more_tab_completions() -> bool:
    return _MULTI_TAB_STATE.value.could_show_more()


# Set up prompt_toolkit key bindings.
def add_key_bindings() -> None:
    custom_bindings = KeyBindings()

    # Need to be careful only to bind with a filter if the state is suitable.
    # Only add more completions if we've seen some results but user hasn't pressed
    # tab a second time yet. Otherwise the behavior should fall back to usual ptk
    # tab behavior (selecting each completion one by one).
    @custom_bindings.add("tab", filter=could_show_more_tab_completions)
    def _(event: KeyPressEvent):
        """
        Add a second tab to show more completions.
        """
        with _MULTI_TAB_STATE.updates() as state:
            state.more_results_requested = True

        trace_completions("More completion results requested", state)

        # Restart completions.
        buf = event.app.current_buffer
        buf.complete_state = None
        buf.start_completion()

    @custom_bindings.add("s-tab")
    def _(event: KeyPressEvent):
        with _MULTI_TAB_STATE.updates() as state:
            state.more_results_requested = True

        trace_completions("More completion results requested", state)

        # Restart completions.
        buf = event.app.current_buffer
        buf.complete_state = None
        buf.start_completion()

    @custom_bindings.add(" ", filter=whitespace_only)
    def _(event: KeyPressEvent):
        """
        Map space at the start of the line to `? ` to invoke an assistant question.
        """
        buf = event.app.current_buffer
        if buf.text == " " or buf.text == "":
            buf.delete_before_cursor(len(buf.text))
            buf.insert_text("? ")
        else:
            buf.insert_text(" ")

    @custom_bindings.add(" ", filter=is_typo_command)
    def _(event: KeyPressEvent):
        """
        If the user types two words and the first word is likely an invalid
        command, jump back to prefix the whole line with `? ` to make it clear we're
        in natural language mode.
        """

        buf = event.app.current_buffer
        text = buf.text.strip()

        if (
            buf.cursor_position == len(buf.text)
            and len(text.split()) >= 2
            and not text.startswith("?")
        ):
            buf.transform_current_line(lambda line: "? " + line)
            buf.cursor_position += 2

        buf.insert_text(" ")

    @custom_bindings.add("enter", filter=whitespace_only)
    def _(_event: KeyPressEvent):
        """
        Suppress enter if the command line is empty, but add a newline above the prompt.
        """
        print_formatted_text("")

    @custom_bindings.add("enter", filter=is_unquoted_assist_request)
    def _(event: KeyPressEvent):
        """
        Automatically add quotes around assistant questions, so there are not
        syntax errors if the command line contains unclosed quotes etc.
        """

        buf = event.app.current_buffer
        text = buf.text.strip()

        question_text = text[1:].strip()
        if not question_text:
            # If the user enters an empty assistant request, treat it as a shortcut to go to the assistant chat.
            buf.delete_before_cursor(len(buf.text))
            buf.insert_text(assistant_chat.__name__)
        else:
            # Convert it to an assistant question starting with a `?`.
            buf.delete_before_cursor(len(buf.text))
            buf.insert_text(assist_request_str(question_text))

        buf.validate_and_handle()

    @custom_bindings.add("enter", filter=is_typo_command)
    def _(event: KeyPressEvent):
        """
        Suppress enter and if possible give completions if the command is just not a valid command.
        """

        buf = event.app.current_buffer
        buf.start_completion()

    # TODO: Also suppress enter if a command or action doesn't meet the required args,
    # selection, or preconditions.
    # Perhaps also have a way to get confirmation if its a rarely used or unexpected command
    # (based on history/suggestions).
    # TODO: Add suggested replacements, e.g. df -> duf, top -> btm, etc.

    @custom_bindings.add("@")
    def _(event: KeyPressEvent):
        """
        Auto-trigger item completions after `@` sign.
        """
        buf = event.app.current_buffer
        buf.insert_text("@")
        buf.start_completion()

    @custom_bindings.add("escape", eager=True, filter=is_completion_menu_active)
    def _(event: KeyPressEvent):
        """
        Close the completion menu when escape is pressed.
        """
        event.app.current_buffer.cancel_completion()

    @custom_bindings.add("c-c", eager=True)
    def _(event):
        """
        Control-C to reset the current buffer. Similar to usual behavior but doesn't
        leave ugly prompt chars.
        """
        print_formatted_text("")
        buf = event.app.current_buffer
        # Abort reverse search/filtering, clear any selection, and reset the buffer.
        search.stop_search()
        buf.exit_selection()
        buf.reset()

    existing_bindings = __xonsh__.shell.shell.prompter.app.key_bindings  # noqa: F821 # pyright: ignore[reportUndefinedVariable]
    merged_bindings = merge_key_bindings([existing_bindings, custom_bindings])
    __xonsh__.shell.shell.prompter.app.key_bindings = merged_bindings  # noqa: F821 # pyright: ignore[reportUndefinedVariable]

    log.info("Added custom %s key bindings.", len(merged_bindings.bindings))
