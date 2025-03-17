from functools import cache
from textwrap import dedent

from kash.config.logger import get_logger
from kash.docs.all_docs import all_docs
from kash.docs.load_help_topics import load_help_src
from kash.utils.common.string_template import StringTemplate

log = get_logger(__name__)

structured_response_template = StringTemplate(
    dedent(
        """
        If a user asks a question, you may offer commentary, a direct answer, and suggested
        commands. Each one is optional.

        You will provide the answer in an AssistantResponse structure.
        Here is a description of how to structure your response, in the form of a Pydantic class
        with documentation on how to use each field:

        {assistant_response_model}

        DO NOT include scripts with shell commands in the `response_text` field.
        Use `suggested_commands` for this, so these commands are not duplicated.

        In response text field, you may mention shell commands within the text `back_ticks` like
        this.

        Within `suggested_commands`, you can return commands that can be used, which can be
        shell commands but usually for content-related tasks will be things like `strip_html` or
        `summarize_as_bullets`.

        In some cases if there is no action available, you can suggest Python code to the user,
        including writing new actions.
        Use the `python_code` field to hold all Python code.
        """
    ),
    ["assistant_response_model"],
)


@cache
def assistant_instructions(is_structured: bool) -> str:
    template = StringTemplate(
        load_help_src("markdown/assistant_instructions_template"),
        ["structured_response_instructions"],
    )
    if is_structured:
        response_model_src = all_docs.source_code.assistant_response_model_src
        structured_response_instructions = structured_response_template.format(
            assistant_response_model=response_model_src
        )
    else:
        structured_response_instructions = ""

    instructions = template.format(
        structured_response_instructions=structured_response_instructions
    )
    instructions_lines = len(instructions.strip().splitlines())

    structured_instructions_len = len(structured_response_instructions.strip().splitlines())
    log.info(
        "Loaded assistant instructions: %s lines, structured instructions: %s lines",
        instructions_lines,
        structured_instructions_len,
    )
    assert instructions_lines > 100 and (not is_structured or structured_instructions_len > 10)
    return instructions
