from InquirerPy.prompts.input import InputPrompt
from InquirerPy.utils import InquirerPyStyle

from kash.config.colors import terminal as colors
from kash.config.text_styles import PROMPT_FORM

custom_style = InquirerPyStyle(
    {
        "questionmark": colors.green_light,
        "answermark": colors.black_light,
        "answer": colors.input,
        "input": colors.input,
        "question": f"{colors.green_light} bold",
        "answered_question": colors.black_light,
        "instruction": colors.black_light,
        "long_instruction": colors.black_light,
        "pointer": colors.cursor,
        "checkbox": colors.green_dark,
        "separator": "",
        "skipped": colors.black_light,
        "validator": "",
        "marker": colors.yellow_dark,
        "fuzzy_prompt": colors.magenta_dark,
        "fuzzy_info": colors.white_dark,
        "fuzzy_border": colors.black_dark,
        "fuzzy_match": colors.magenta_dark,
        "spinner_pattern": colors.green_light,
        "spinner_text": "",
    }
)


def prompt_simple_string(prompt_text: str = "", prompt_symbol: str = f"{PROMPT_FORM}") -> str:
    """
    Simple prompt from the user for a simple string.
    """
    prompt_text = prompt_text.strip()
    sep = "\n" if len(prompt_text) > 15 else " "
    prompt_message = f"{prompt_text}{sep}{prompt_symbol}"
    try:
        response = InputPrompt(message=prompt_message, style=custom_style).execute()
    except EOFError:
        return ""
    return response
