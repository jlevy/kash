from kash.actions.core.webpage_config import webpage_config
from kash.actions.core.webpage_generate import webpage_generate
from kash.commands.base.show_command import show
from kash.config.logger import get_logger
from kash.exec import kash_action
from kash.exec.preconditions import has_text_body, is_html
from kash.exec_model.commands_model import Command
from kash.exec_model.shell_model import ShellResult
from kash.model import ActionInput, ActionResult

log = get_logger(__name__)


@kash_action(
    precondition=is_html | has_text_body,
)
def show_webpage(input: ActionInput) -> ActionResult:
    """
    Show text, Markdown, or HTML as a nicely formatted webpage.
    """
    config_result = webpage_config(input)

    log.message("Configured web page: %s", config_result)
    result = webpage_generate(ActionInput(items=config_result.items))

    # Automatically show the result.
    result.shell_result = ShellResult(display_command=Command.assemble(show))
    return result
