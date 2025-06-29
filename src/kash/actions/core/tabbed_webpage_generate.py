from kash.config.logger import get_logger
from kash.exec import kash_action
from kash.exec.preconditions import is_data
from kash.model import ONE_ARG, ActionInput, ActionResult, FileExt, Format, Item, ItemType, Param
from kash.web_gen import tabbed_webpage

log = get_logger(__name__)


@kash_action(
    expected_args=ONE_ARG,
    precondition=is_data,
    params=(Param("add_title", "Add a title to the page body.", type=bool),),
)
def tabbed_webpage_generate(input: ActionInput, add_title: bool = False) -> ActionResult:
    """
    Generate a tabbed web page from a config item for the tabbed template.
    """
    config_item = input.items[0]
    html = tabbed_webpage.tabbed_webpage_generate(
        config_item, add_title_h1=add_title, show_theme_toggle=True
    )

    webpage_item = Item(
        title=config_item.title,
        type=ItemType.export,
        format=Format.html,
        file_ext=FileExt.html,
        body=html,
    )

    return ActionResult([webpage_item])
