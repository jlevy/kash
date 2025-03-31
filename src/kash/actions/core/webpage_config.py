from kash.config.logger import get_logger
from kash.exec import kash_action
from kash.model import ActionInput, ActionResult
from kash.utils.errors import InvalidInput
from kash.web_gen import tabbed_webpage

log = get_logger(__name__)


@kash_action()
def webpage_config(input: ActionInput) -> ActionResult:
    """
    Set up a web page config with optional tabs for each page of content. Uses first item as the page title.
    """
    for item in input.items:
        if not item.body:
            raise InvalidInput(f"Item must have a body: {item}")

    config_item = tabbed_webpage.webpage_config(input.items)

    return ActionResult([config_item])
