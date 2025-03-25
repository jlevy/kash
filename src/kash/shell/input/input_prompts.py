from InquirerPy.prompts.confirm import ConfirmPrompt
from InquirerPy.prompts.input import InputPrompt
from InquirerPy.prompts.list import ListPrompt

from kash.config.text_styles import PROMPT_FORM
from kash.shell.input.inquirer_styles import custom_style

DEFAULT_INSTRUCTION = "(Ctrl-C to cancel.)"


def input_simple_string(
    prompt_text: str,
    default: str = "",
    prompt_symbol: str = f"{PROMPT_FORM}",
    instruction: str = DEFAULT_INSTRUCTION,
) -> str:
    """
    Simple prompt from the user for a simple string.
    """
    prompt_text = prompt_text.strip()
    sep = "\n" if len(prompt_text) > 15 else " "
    prompt_message = f"{prompt_text}{sep}{prompt_symbol}"
    try:
        response = InputPrompt(
            message=prompt_message, style=custom_style, default=default, instruction=instruction
        ).execute()
    except EOFError:
        return ""
    return response


def input_confirm(
    prompt_text: str, default: bool = False, instruction: str = DEFAULT_INSTRUCTION
) -> bool:
    response = ConfirmPrompt(
        message=prompt_text, style=custom_style, default=default, instruction=instruction
    ).execute()
    return response


def input_choice(
    prompt_text: str,
    choices: list[str],
    default: str | None = None,
    mandatory: bool = False,
    instruction: str = DEFAULT_INSTRUCTION,
) -> str:
    response: str = ListPrompt(
        message=prompt_text,
        style=custom_style,
        choices=choices,
        default=default,
        mandatory=mandatory,
        instruction=instruction,
        show_cursor=False,
    ).execute()
    return response
