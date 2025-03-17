from kash.config.logger import get_logger
from kash.exec import kash_action
from kash.exec.preconditions import is_config
from kash.model import ONE_ARG, ActionInput, ActionResult, FileExt, Format, Item, ItemType
from kash.web_gen import tabbed_webpage

log = get_logger(__name__)


@kash_action(
    expected_args=ONE_ARG,
    precondition=is_config,
)
def webpage_generate(input: ActionInput) -> ActionResult:
    """
    Generate a web page from a configured web page item.
    """
    config_item = input.items[0]
    html = tabbed_webpage.webpage_generate(config_item)

    webpage_item = Item(
        title=config_item.title,
        type=ItemType.export,
        format=Format.html,
        file_ext=FileExt.html,
        body=html,
    )

    return ActionResult([webpage_item])
