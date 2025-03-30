from enum import Enum

from prompt_toolkit.application import get_app

from kash.shell.input.input_prompts import input_choice


class SuggestionResponse(Enum):
    """
    Response from the user to a suggestion.
    """

    think_more = "Think more"
    give_more_instructions = "Give more instructions"
    cancel = "Cancel"


def confirm_commands(prompt_text: str, command_strs: list[str]) -> str | None:
    choices = [
        *command_strs,
        SuggestionResponse.think_more.value,
        SuggestionResponse.give_more_instructions.value,
        SuggestionResponse.cancel.value,
    ]

    response = input_choice(
        prompt_text,
        choices,
        default=command_strs[0],
        instruction="You can edit all commands before running them.",
    )
    return response


def insert_command_into_buffer(command: str):
    """
    Insert a command into the current shell buffer.
    """
    app = get_app()
    buf = app.current_buffer
    buf.reset()
    buf.insert_text(command)

    # Move cursor to end.
    buf.cursor_position = len(command)
