from InquirerPy.utils import InquirerPyKeybindings, InquirerPyStyle
from prompt_toolkit.application import get_app

from kash.config.colors import terminal as colors

custom_style = InquirerPyStyle(
    # See https://inquirerpy.readthedocs.io/en/latest/pages/style.html#default-style
    {
        "questionmark": colors.green_light,
        "answermark": colors.black_light,
        "answer": colors.input,
        "input": colors.input,
        "question": f"{colors.green_light} bold",
        "answered_question": colors.black_light,
        "instruction": colors.black_light,
        "long_instruction": f"{colors.black_light} noreverse",
        "bottom-toolbar": f"{colors.black_light} noreverse",
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


custom_keybindings: InquirerPyKeybindings = {
    "answer": [{"key": "enter"}],  # answer the prompt
    "interrupt": [{"key": "c-c"}, {"key": "escape"}],  # raise KeyboardInterrupt
    "skip": [{"key": "c-z"}],  # skip the prompt
}


def configure_inquirer() -> None:
    # Try to make inquirer responsive for forms, in particular for escape.
    # TODO: Better approach? Esc is still slower than other keybindings.
    get_app().ttimeoutlen = 0.01
    get_app().timeoutlen = 0.01
