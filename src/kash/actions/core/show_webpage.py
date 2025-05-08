from kash.actions.core.render_as_html import render_as_html
from kash.commands.base.show_command import show
from kash.exec import kash_action
from kash.exec.preconditions import has_full_html_page_body, has_text_body, is_html
from kash.exec_model.args_model import ONE_OR_MORE_ARGS
from kash.exec_model.commands_model import Command
from kash.exec_model.shell_model import ShellResult
from kash.model import ActionInput, ActionResult


@kash_action(
    expected_args=ONE_OR_MORE_ARGS,
    precondition=(is_html | has_text_body) & ~has_full_html_page_body,
)
def show_webpage(input: ActionInput) -> ActionResult:
    """
    Show text, Markdown, or HTML as a nicely formatted webpage.
    """
    result = render_as_html(input)

    # Automatically show the result.
    result.shell_result = ShellResult(display_command=Command.assemble(show))
    return result
