import re
from dataclasses import dataclass
from typing import Any, cast

from funlog import log_calls
from prompt_toolkit import search
from prompt_toolkit.application import get_app
from prompt_toolkit.filters import Condition
from prompt_toolkit.key_binding import KeyBindings, merge_key_bindings
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.shortcuts import print_formatted_text
from xonsh.built_ins import XSH
from xonsh.completers.completer import add_one_completer
from xonsh.completers.tools import (
    CompleterResult,
    CompletionContext,
    contextual_completer,
    non_exclusive_completer,
)
from xonsh.parsers.completion_context import CommandContext

from kash.actions.core.assistant_chat import assistant_chat
from kash.config.logger import get_logger
from kash.exec.action_registry import get_all_actions_defaults
from kash.exec.command_registry import get_all_commands
from kash.help.function_param_info import annotate_param_info
from kash.model.params_model import COMMON_SHELL_PARAMS, Param
from kash.shell.completions.completion_types import CompletionGroup, ScoredCompletion
from kash.shell.completions.shell_completions import (
    get_command_and_action_completions,
    get_help_completions_lexical,
    get_help_completions_semantic,
    get_item_completions,
    get_std_command_completions,
    trace_completions,
)
from kash.shell.ui.shell_syntax import assist_request_str
from kash.utils.common.atomic_var import AtomicVar
from kash.utils.errors import ApiResultError, InvalidState
from kash.xonsh_custom.command_nl_utils import as_nl_words, looks_like_nl
from kash.xonsh_custom.shell_which import is_valid_command

log = get_logger(__name__)


# We want to keep completion fast, so let's log when it's slow.
SLOW_COMPLETION = 0.15

MIN_COMMAND_COMPLETIONS = 5


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


def full_commandline(context: CompletionContext) -> str:
    # XXX Seems like command.text_before_cursor is not always the whole command line,
    # especially for NL questions, so we first check the python code if available.
    text = (
        context.python
        and context.python.multiline_code
        or (context.command and context.command.text_before_cursor or "")
    )
    return text


def commandline_as_nl(context: CompletionContext) -> str:
    if not context.command:
        return ""

    return as_nl_words(full_commandline(context))


def is_nl_words(context: CompletionContext) -> bool:
    """
    Check if the input looks like plain natural language text, i.e. word chars,
    possibly with ? or hyphens/apostrophes when inside words but not other
    code or punctuation.
    """
    if not context.command:
        return False
    return looks_like_nl(full_commandline(context))


def is_assist_request(context: CompletionContext) -> bool:
    """
    Check if this is an NL assistant request, based on whether it
    starts with a space or `?`:

    `<space>some question or request`
    `?some question or request`
    `? some question or request`
    """
    text = full_commandline(context)
    return text.startswith(" ") or text.startswith("?")


def is_recognized_command(context: CompletionContext) -> bool:
    return not is_assist_request(context) and bool(
        context.command
        and len(context.command.args) > 0
        and is_valid_command(context.command.args[0].value)
    )


def set_replace_prefixes(completions: set[ScoredCompletion], context: CompletionContext) -> None:
    """
    If the completions are marked as replace_input, set the prefix_len to the
    length of the text before the cursor.
    """
    if context.command:
        prefix_len = len(full_commandline(context)) + 1
        for completion in completions:
            if completion.replace_input:
                completion.prefix_len = prefix_len


def post_process(
    completions: set[ScoredCompletion] | None, context: CompletionContext
) -> CompleterResult:
    if completions:
        set_replace_prefixes(completions, context)
        return cast(CompleterResult, completions)
    else:
        return None


@contextual_completer
@log_calls(level="info", if_slower_than=SLOW_COMPLETION)
def bare_completer(context: CompletionContext) -> CompleterResult:
    """
    Completes on bare command line. Exclusive since we want control over the list
    and to be fast.
    """

    if is_recognized_command(context):
        return None

    trace_completions(f"bare_completer: {context.command!r}")

    if not commandline_as_nl(context):
        bare_completions = get_help_completions_lexical("", include_bare_qm=True)
        return post_process(bare_completions, context)

    return None


@contextual_completer
@non_exclusive_completer
@log_calls(level="info", if_slower_than=SLOW_COMPLETION)
def command_completer(context: CompletionContext) -> CompleterResult:
    """
    Completes on kash commands and actions. Non-exclusive so xonsh shell completions can
    be used too.
    """

    if context.command and context.command.arg_index == 0:
        prefix = context.command.prefix
        completions = get_command_and_action_completions(prefix)
        trace_completions(f"command_completer: {prefix!r}", completions)
        if len(completions) < MIN_COMMAND_COMPLETIONS:
            trace_completions(
                f"command_completer: Got only {len(completions)} command completions, trying help question completions",
                completions,
            )
            help_completions = help_completer(context)
            if help_completions:
                completions = completions | cast(set, help_completions)

        return post_process(completions, context)

    return None


@contextual_completer
@non_exclusive_completer
@log_calls(level="info", if_slower_than=SLOW_COMPLETION)
def recommended_shell_completer(context: CompletionContext) -> CompleterResult:
    """
    Completes on shell commands.
    """
    if context.command and context.command.arg_index == 0:
        prefix = context.command.prefix
        completions = get_std_command_completions(prefix)
        return post_process(completions, context)
    return None


@contextual_completer
@log_calls(level="info", if_slower_than=SLOW_COMPLETION)
def item_completer(context: CompletionContext) -> CompleterResult:
    """
    If the current command is an action, complete with paths that match the precondition
    for that action.
    """
    actions = get_all_actions_defaults()

    try:
        if context.command and context.command.arg_index >= 1:
            action_name = context.command.args[0].value
            action = actions.get(action_name)
            prefix = context.command.prefix
            if action and action.precondition:
                completions = get_item_completions(prefix, action.precondition)
                trace_completions(f"item_completer: {prefix!r}", completions)
                return post_process(completions, context)
    except InvalidState:
        return None
    return None


@contextual_completer
@log_calls(level="info", if_slower_than=SLOW_COMPLETION)
def command_path_completer(context: CompletionContext) -> CompleterResult:
    """
    If the current command a kash command that takes a file path, complete with
    paths in the current directory.
    """
    from xonsh.completers.path import contextual_complete_path

    commands = get_all_commands()

    if context.command and context.command.arg_index >= 1:
        command_name = context.command.args[0].value
        param_index = context.command.arg_index - 1
        command = commands.get(command_name)
        if command:
            param_info = annotate_param_info(command)
            # If this parameter is a path, complete with paths using xonsh's path completer.
            # TODO: Augment path completions to add more rich info about files/directories
            # (number of files in a subdir, file type of a file, etc.)
            if param_info and len(param_info) > param_index and param_info[param_index].is_path:
                completions, lprefix = contextual_complete_path(context.command)
                scored_completions = {ScoredCompletion.from_unscored(c) for c in completions}
                trace_completions(f"command_file_completer: {lprefix!r}", scored_completions)
                return post_process(scored_completions, context)
    return None


@contextual_completer
@log_calls(level="info", if_slower_than=SLOW_COMPLETION)
def at_prefix_completer(context: CompletionContext) -> CompleterResult:
    """
    Completes items in the current workspace if prefixed with '@' sign.
    """
    try:
        if context.command:
            prefix = context.command.prefix
            if prefix.startswith("@"):
                prefix = prefix.lstrip("@")
                if context.command.arg_index >= 1:
                    completions = get_item_completions(prefix)
                    trace_completions(f"at_prefix_completer: {prefix!r}", completions)
                else:
                    # Just return top help completions for @ prefix as the command.
                    completions = get_help_completions_lexical("", include_bare_qm=True)
                    trace_completions(f"at_prefix_completer: {prefix!r}", completions)
                return post_process(completions, context)

    except InvalidState:
        return None
    return None


@contextual_completer
@non_exclusive_completer
@log_calls(level="info", if_slower_than=SLOW_COMPLETION)
def help_completer(context: CompletionContext) -> CompleterResult:
    """
    Suggest help FAQs and commands. These replace the whole command line.
    This aims to only activate if the text is likely a natural language.
    If it's a command, let other completions handle it.
    We support two levels, lexical and semantic, and activate the semantic
    completions on a second tab press.
    """
    if context.command:
        # Full query is full command line so far, lightly cleaned up.
        query = commandline_as_nl(context)
        num_words = len(query.split())
        is_long = num_words > 4
        is_recognized = is_recognized_command(context)
        is_nl = is_nl_words(context)
        show_immediate_help = not is_recognized and is_nl
        allow_subsequent_help = is_long

        trace_completions(f"help_completer: {query!r} {is_long=} {is_recognized=} {is_nl=}")

        # Don't do full help on completions on short commands like "cd foo".
        if not query:
            return None

        with _MULTI_TAB_STATE.updates() as state:
            # If the user has already typed a command we recognize, don't ever give help
            # unless it's quite a long command.
            if not show_immediate_help and not state.more_results_requested:
                trace_completions(
                    "help_completer: Skipping help completions since command is recognized"
                )
                state.reset_first_results(context.command)
                return None
            if (
                context.command == state.last_context
                and state.more_results_requested
                and allow_subsequent_help
            ):
                # User hit tab again so let's fill in slower semantic completions.
                if state.more_completions is None:
                    trace_completions(
                        f"help_completer: {query!r}: Adding more semantic help completions", state
                    )
                    try:
                        state.more_completions = get_help_completions_semantic(query)
                    except ApiResultError as e:
                        log.info("Skipping semantic help since embedding API unavailable: %s", e)
                        state.more_completions = None
            else:
                state.reset_first_results(context.command)

            more_completions = set(state.more_completions or set())

        lex_completions = get_help_completions_lexical(query, include_bare_qm=True)
        completions = lex_completions | more_completions
        trace_completions(f"help_completer: {query!r}: Combined help completions", completions)
        return post_process(completions, context)

    return None


def _params_for_command(command_name: str) -> list[Param[Any]] | None:
    command = get_all_commands().get(command_name)
    action = get_all_actions_defaults().get(command_name)

    if command:
        return annotate_param_info(command)
    elif action:
        return list(action.params)
    else:
        return None


def _param_completions(params: list[Param[Any]], prefix: str) -> list[ScoredCompletion]:
    completions = [
        ScoredCompletion(
            param.shell_prefix,
            group=CompletionGroup.relev_opt,
            display=param.display,
            description=param.description or "",
            append_space=param.is_bool,
        )
        for param in params
        if param.shell_prefix.startswith(prefix)  # prefix includes leading dashes
    ]
    for p in COMMON_SHELL_PARAMS.values():
        if p.shell_prefix.startswith(prefix):
            completions.append(
                ScoredCompletion(
                    p.shell_prefix,
                    group=CompletionGroup.top_suggestion,
                    display=p.display,
                    description=p.description or "",
                )
            )
    return completions


def _enum_value_completions(param: Param[Any], prefix: str) -> list[ScoredCompletion]:
    """
    Get completions for parameter values that start with the given prefix.
    Handles both enum and `str` parameters with valid or suggested values.
    """
    valid_values = param.valid_values
    if valid_values:
        trace_completions(
            f"_enum_value_completions: valid values for param {param.name}", valid_values
        )
        values = [
            ScoredCompletion(
                param.shell_prefix + value,
                group=CompletionGroup.relev_opt,
                display=value,
                replace_input=False,
                append_space=True,
            )
            for value in valid_values
            if value.startswith(prefix)
        ]
        trace_completions(f"_enum_value_completions: matches for param {param.name}", values)
        return values
    return []


@contextual_completer
@non_exclusive_completer
@log_calls(level="info", if_slower_than=SLOW_COMPLETION)
def options_completer(context: CompletionContext) -> CompleterResult:
    """
    Suggest options completions after a `-` or `--` on the command line.
    """
    if context.command and context.command.arg_index > 0:
        prefix = context.command.prefix
        command_name = context.command.args[0].value

        params = _params_for_command(command_name)
        is_command = params is not None
        prefix_empty = not prefix.strip()
        # Are we inside an option, but not in the value?
        completing_option_name = prefix.startswith("-") and "=" not in prefix

        if is_command and (prefix_empty or completing_option_name):
            completions = _param_completions(params, prefix)

            if completions and "--help".startswith(prefix):
                completions.append(
                    ScoredCompletion(
                        "--help",
                        description="Show full help for this command.",
                        group=CompletionGroup.top_suggestion,
                    )
                )

            trace_completions(
                f"options_completer: {prefix!r}: {len(completions)} matches out of {len(params)} params",
                completions,
            )

            return set(completions) if completions else None


@contextual_completer
@non_exclusive_completer
@log_calls(level="info", if_slower_than=SLOW_COMPLETION)
def options_enum_completer(context: CompletionContext) -> CompleterResult:
    """
    Suggest completions for enum parameter values after an option with '='.
    """
    if context.command and context.command.arg_index >= 1:
        prefix = context.command.prefix
        command_name = context.command.args[0].value

        # Check if we're completing after an '='.
        if "=" in prefix:
            option_name, value_prefix = prefix.split("=", 1)
            option_name = option_name.lstrip("-")

            params = _params_for_command(command_name)
            trace_completions(
                f"options_enum_completer: for command: {command_name} option: {option_name}",
                params,
            )

            # Find the matching param.
            if params:
                for param in params:
                    completions = None
                    if param.name == option_name and param.valid_values:
                        completions = _enum_value_completions(param, value_prefix)
                    return set(completions) if completions else None

    return None


# TODO: Other contextual completions needed for specific kash commands:
# - `help`
# - `source_code`


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


def load_completers():
    add_one_completer("command_completer", command_completer, "start")
    add_one_completer("recommended_shell_completer", recommended_shell_completer, "start")
    add_one_completer("item_completer", item_completer, "start")
    add_one_completer("at_prefix_completer", at_prefix_completer, "start")
    add_one_completer("help_completer", help_completer, "start")
    add_one_completer("options_completer", options_completer, "start")
    add_one_completer("options_enum_completer", options_enum_completer, "start")
    add_one_completer("bare_completer", bare_completer, "start")

    log.info("Loaded %s completers.", len(XSH.completers))
