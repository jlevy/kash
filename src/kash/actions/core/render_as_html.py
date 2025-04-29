from kash.actions.core.webpage_config import webpage_config
from kash.actions.core.webpage_generate import webpage_generate
from kash.exec import kash_action
from kash.exec.preconditions import has_text_body, is_html
from kash.model import ActionInput, ActionResult


@kash_action(
    precondition=is_html | has_text_body,
)
def render_as_html(input: ActionInput) -> ActionResult:
    """
    Convert text, Markdown, or HTML to pretty, formatted HTML using the kash default
    page template.
    """
    config_result = webpage_config(input)
    result = webpage_generate(ActionInput(items=config_result.items))
    return result
