import inspect
from pathlib import Path
from typing import Callable, List, Optional, Type

from thefuzz import fuzz

from kash.config.text_styles import COLOR_HINT
from kash.docs.all_docs import all_docs
from kash.errors import FileNotFound, InvalidInput, NoMatch
from kash.exec.action_registry import look_up_action_class
from kash.exec.command_registry import CommandFunction, look_up_command
from kash.help.assistant import assist_preamble, assistance_unstructured
from kash.help.docstring_utils import parse_docstring
from kash.help.function_param_info import annotate_param_info
from kash.help.help_types import Faq
from kash.help.tldr_help import tldr_help
from kash.llm_tools.chat_format import ChatHistory, ChatMessage, ChatRole
from kash.llm_tools.llm_messages import Message
from kash.model.actions_model import Action
from kash.model.language_models import LLM
from kash.model.params_model import COMMON_SHELL_PARAMS, Param, RUNTIME_ACTION_PARAMS
from kash.model.preconditions_model import Precondition

from kash.shell_output.shell_output import (
    cprint,
    format_name_and_description,
    format_name_and_value,
    print_help,
    print_markdown,
    PrintHooks,
)


GENERAL_HELP = (
    "For more information, ask the assistant a question (press space or `?`) or check `help`."
)


def _print_command_help(
    name: str,
    description: Optional[str] = None,
    param_info: Optional[List[Param]] = None,
    precondition: Optional[Precondition] = None,
    verbose: bool = True,
    is_action: bool = False,
    extra_note: Optional[str] = None,
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


def source_code_path(command_or_action: CommandFunction | Action | Type[Action]) -> Path:
    """
    Get the path to the source code for a command or action.
    """
    # Action classes and instances should have a __source_path__ attribute, because
    # the original source may have been wrapped within another source file.
    source_path = getattr(command_or_action, "__source_path__", None)
    if not source_path and isinstance(command_or_action, Callable):
        # Commands are just the original function with a decorator in the same source file,
        # so inspect should be accurate.
        source_path = inspect.getsourcefile(command_or_action)
    if not source_path:
        raise FileNotFound(f"No source path found for command or action: {command_or_action}")

    resolved_path = Path(source_path).resolve()
    if not resolved_path.exists():
        raise FileNotFound(
            f"File not found for command or action {command_or_action}: {resolved_path}"
        )

    return resolved_path


def look_up_faq(text: str) -> Faq:
    """
    Look up a FAQ by question. Requires nearly an exact match. For approximate
    matching use embeddings.
    """

    def faq_match(text: str, faq: Faq) -> bool:
        def normalize(s: str) -> str:
            return s.strip(" ?").lower()

        normalized_text = normalize(text)
        normalized_question = normalize(faq.question)
        ratio = fuzz.ratio(normalized_text, normalized_question)

        if len(normalized_text) <= 10:
            return ratio >= 98
        else:
            return ratio >= 95

    for faq in all_docs.faqs:
        if faq_match(text, faq):
            return faq

    raise NoMatch()


def print_explain_command(text: str, assistant_model: Optional[LLM] = None):
    """
    Explain a command or action or give a brief explanation of something.
    Checks tldr and help docs first. If `assistant_model` is provided and docs
    are not available, use the assistant.
    """
    text = text.strip()

    tldr_help_str = tldr_help(text, drop_header=True)
    if tldr_help_str:
        cprint(
            format_name_and_description(f"`{text}`", tldr_help_str, extra_note="(shell command)")
        )
        return

    try:
        command = look_up_command(text)
        print_command_function_help(command)
        return
    except InvalidInput:
        pass

    try:
        action_cls = look_up_action_class(text)
        print_action_help(action_cls.create(None))
        return
    except InvalidInput:
        pass

    try:
        faq = look_up_faq(text)
        PrintHooks.spacer()
        cprint("(Answer from FAQ:)", style=COLOR_HINT)
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
