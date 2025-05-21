from kash.actions.core.tabbed_webpage_config import tabbed_webpage_config
from kash.actions.core.tabbed_webpage_generate import tabbed_webpage_generate
from kash.exec import kash_action
from kash.exec.preconditions import has_fullpage_html_body, has_html_body, has_simple_text_body
from kash.exec_model.args_model import ONE_OR_MORE_ARGS
from kash.model import ActionInput, ActionResult, Param
from kash.model.items_model import ItemType
from kash.utils.file_utils.file_formats_model import Format
from kash.web_gen.simple_webpage import simple_webpage_render


@kash_action(
    expected_args=ONE_OR_MORE_ARGS,
    precondition=(has_html_body | has_simple_text_body) & ~has_fullpage_html_body,
    params=(Param("no_title", "Don't add a title to the page body.", type=bool),),
)
def render_as_html(input: ActionInput, no_title: bool = False) -> ActionResult:
    """
    Convert text, Markdown, or HTML to pretty, formatted HTML using a clean
    and simple page template. Supports GFM-flavored Markdown tables and footnotes.

    If it's a single input, the output is a simple HTML page.
    If it's multiple inputs, the output is a tabbed HTML page.

    This adds a header, footer, etc. so should be used on a plain document or HTML basic
    page, not a full HTML page with header and body already present.
    """
    if len(input.items) == 1:
        input_item = input.items[0]
        html_body = simple_webpage_render(input_item, add_title_h1=not no_title)
        result_item = input_item.derived_copy(
            type=ItemType.export, format=Format.html, body=html_body
        )
        return ActionResult([result_item])
    else:
        config_result = tabbed_webpage_config(input)
        return tabbed_webpage_generate(
            ActionInput(items=config_result.items), add_title=not no_title
        )
