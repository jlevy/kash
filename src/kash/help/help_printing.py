from kash.config.logger import get_logger
from kash.config.text_styles import STYLE_HINT
from kash.exec.action_registry import look_up_action_class
from kash.exec.command_registry import CommandFunction, look_up_command
from kash.help.assistant import assist_preamble, assistance_unstructured
from kash.help.docstring_utils import parse_docstring
from kash.help.function_param_info import annotate_param_info
from kash.help.help_lookups import look_up_faq
from kash.help.tldr_help import tldr_help
from kash.llm_utils import LLM
from kash.llm_utils.llm_messages import Message
from kash.model.actions_model import Action
from kash.model.params_model import COMMON_SHELL_PARAMS, RUNTIME_ACTION_PARAMS, Param
from kash.model.preconditions_model import Precondition
from kash.shell.output.shell_output import (
    PrintHooks,
    cprint,
    format_name_and_description,
    format_name_and_value,
    print_help,
    print_markdown,
)
from kash.utils.errors import InvalidInput, NoMatch
from kash.utils.file_formats.chat_format import ChatHistory, ChatMessage, ChatRole

log = get_logger(__name__)

GENERAL_HELP = (
    "For more information, ask the assistant a question (press space or `?`) or check `help`."
)


def _print_command_help(
    name: str,
    description: str | None = None,
    param_info: list[Param] | None = None,
    precondition: Precondition | None = None,
    verbose: bool = True,
    is_action: bool = False,  # pyright: ignore[reportUnusedParameter]
    extra_note: str | None = None,
):
    command_str = f"the `{name}` command" if name else "this command"

    cprint()

    if not description:
        print_help(f"Sorry, no help available for {command_str}.")
    else:
        docstring = parse_docstring(description)

        cprint(format_name_and_description(f"`{name}`", docstring.body, extra_note=extra_note))

        if precondition:
            cprint()
            cprint("Precondition: " + str(precondition), style="markdown.emph")

        if param_info:
            cprint()
            cprint("Options:", style="markdown.emph")

            for param in param_info:
                cprint()
                full_desc = param.full_description

                if param.name in docstring.param:
                    param_desc = docstring.param[param.name]
                    if param_desc:
                        param_desc += "\n\n"
                    param_desc += param.valid_and_default_values
                elif full_desc:
                    param_desc = full_desc
                else:
                    param_desc = "(No parameter description)"

                cprint(format_name_and_value(f"`{param.display}`", param_desc))

    if verbose:
        cprint()
        print_help(GENERAL_HELP)


def print_command_function_help(command: CommandFunction, verbose: bool = True):
    params = annotate_param_info(command) + list(COMMON_SHELL_PARAMS.values())

    _print_command_help(
        command.__name__,
        command.__doc__ if command.__doc__ else "",
        param_info=params,
        verbose=verbose,
        is_action=False,
        extra_note="(kash command)",
    )


def print_action_help(action: Action, verbose: bool = True):
    params = (
        list(action.params)
        + list(RUNTIME_ACTION_PARAMS.values())
        + list(COMMON_SHELL_PARAMS.values())
    )

    _print_command_help(
        action.name,
        action.description,
        param_info=params,
        precondition=action.precondition,
        verbose=verbose,
        is_action=True,
        extra_note="(kash action)",
    )


def print_explain_command(text: str, assistant_model: LLM | None = None):
    """
    Explain a command or action or give a brief explanation of something.
    Checks tldr and help docs first. If `assistant_model` is provided and docs
    are not available, use the assistant.
    """
    text = text.strip()

    words = text.split()
    if not words:
        raise NoMatch("No command provided")

    if len(words) == 1:
        first_word = words[0]
        # Use first word as a command and check for TLDR help.
        try:
            tldr_help_str = tldr_help(first_word, drop_header=True)
            if tldr_help_str:
                cprint(
                    format_name_and_description(
                        f"`{text}`", tldr_help_str, extra_note="(shell command)"
                    )
                )
                return
        except Exception as e:
            log.info("No TLDR help found for %s: %s", text, e)
            pass

        # Next check if we have help docs.
        try:
            command = look_up_command(first_word)
            print_command_function_help(command)
            return
        except InvalidInput:
            pass

        try:
            action_cls = look_up_action_class(first_word)
            print_action_help(action_cls.create(None))
            return
        except InvalidInput:
            pass

    try:
        faq = look_up_faq(text)
        PrintHooks.spacer()
        cprint("(Answer from FAQ:)", style=STYLE_HINT)
        PrintHooks.spacer()
        print_markdown(faq.answer)
        return
    except NoMatch:
        pass

    if assistant_model:
        chat_history = ChatHistory()

        # Give the LLM full context on kash APIs.
        # But we do this here lazily to prevent circular dependencies.
        system_message = Message(
            assist_preamble(is_structured=False, skip_api_docs=False, base_actions_only=False)
        )
        chat_history.extend(
            [
                ChatMessage(ChatRole.system, system_message),
                ChatMessage(ChatRole.user, f"Can you explain this succinctly: {text}"),
            ]
        )

        response = assistance_unstructured(chat_history.as_chat_completion(), model=assistant_model)
        help_str = response.content
        print_markdown(help_str)
        return

    raise NoMatch(f"Sorry, no help found for `{text}`")
