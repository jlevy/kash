from InquirerPy.prompts.confirm import ConfirmPrompt
from InquirerPy.prompts.input import InputPrompt

from kash.config.text_styles import PROMPT_FORM
from kash.shell.input.inquirer_styles import custom_style


def input_simple_string(
    prompt_text: str = "",
    default: str = "",
    prompt_symbol: str = f"{PROMPT_FORM}",
) -> str:
    """
    Simple prompt from the user for a simple string.
    """
    prompt_text = prompt_text.strip()
    sep = "\n" if len(prompt_text) > 15 else " "
    prompt_message = f"{prompt_text}{sep}{prompt_symbol}"
    try:
        response = InputPrompt(
            message=prompt_message, style=custom_style, default=default
        ).execute()
    except EOFError:
        return ""
    return response


def input_confirm(prompt_text: str = "Confirm?", default: bool = False) -> bool:
    response = ConfirmPrompt(message=prompt_text, style=custom_style, default=default).execute()
    return response
