from rich.text import Text

from kash.config.text_styles import COLOR_HINT, EMOJI_ASSISTANT
from kash.help.help_pages import print_see_also
from kash.model.assistant_response_model import AssistantResponse
from kash.model.language_models import LLMName
from kash.shell_output.shell_output import (
    PadStyle,
    PrintHooks,
    cprint,
    print_code_block,
    print_markdown,
    print_style,
)


def print_assistant_heading(model: LLMName) -> None:
    assistant_name = Text(f"{EMOJI_ASSISTANT} Kash Assistant", style="markdown.h3")
    info = Text(f"({model})", style=COLOR_HINT)
    cprint(assistant_name + " " + info)


def print_assistant_response(response: AssistantResponse, model: LLMName) -> None:
    with print_style(PadStyle.PAD):
        print_assistant_heading(model)
        PrintHooks.spacer()

        if response.response_text:
            # TODO: indicate confidence level
            # TODO: Some other visual indication this is assistance, without losing Markdown coloring.
            print_markdown(response.response_text)

        if response.suggested_commands:
            formatted_commands = "\n\n".join(c.script_str for c in response.suggested_commands)
            cprint("Suggested commands:", style="markdown.emph")
            print_code_block(formatted_commands)

        if response.python_code:
            cprint("Python code:", style="markdown.emph")
            print_code_block(response.python_code, format="python")

        if response.see_also:
            print_see_also(response.see_also)
