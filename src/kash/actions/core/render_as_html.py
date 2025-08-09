from pathlib import Path

from sidematter_format import Sidematter, copy_sidematter

from kash.actions.core.tabbed_webpage_config import tabbed_webpage_config
from kash.actions.core.tabbed_webpage_generate import tabbed_webpage_generate
from kash.config.logger import get_logger
from kash.exec import kash_action
from kash.exec.preconditions import has_fullpage_html_body, has_html_body, has_simple_text_body
from kash.exec_model.args_model import ONE_OR_MORE_ARGS
from kash.model import ActionInput, ActionResult, Param
from kash.model.items_model import ItemType
from kash.utils.file_utils.file_formats_model import Format
from kash.utils.text_handling.markdown_utils import rewrite_image_urls
from kash.web_gen.webpage_render import render_webpage
from kash.workspaces.workspaces import current_ws

log = get_logger(__name__)


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

        result_item = input_item.preassembled_copy(type=ItemType.export, format=Format.html)
        ws = current_ws()

        assert input_item.store_path

        old_prefix = Sidematter(Path(input_item.store_path)).assets_dir.name
        new_prefix = Sidematter(ws.assign_store_path(result_item)).assets_dir.name

        log.message("Result item: %s", result_item)
        log.message("Rewriting doc image paths: `%s` -> `%s`", old_prefix, new_prefix)

        # Rewrite image paths to be relative to the workspace.
        assert input_item.body
        if input_item.format in (Format.markdown, Format.md_html):
            rewritten_body = rewrite_image_urls(input_item.body, old_prefix, new_prefix)
        else:
            rewritten_body = input_item.body

        rewritten_item = input_item.derived_copy(body=rewritten_body)

        result_item.body = render_webpage(
            title=input_item.pick_title(),
            content_html=rewritten_item.body_as_html(),
            thumbnail_url=input_item.thumbnail_url,
            add_title_h1=not no_title,
            show_theme_toggle=True,
        )

        # Manually copy over metadata *and* assets. This makes image assets work.
        result_path = ws.assign_store_path(result_item)
        log.message(
            "Copying sidematter and assets: %s -> %s",
            input_item.store_path,
            result_item.store_path,
        )
        copy_sidematter(
            src_path=ws.base_dir / input_item.store_path,
            dest_path=result_path,
            make_parents=True,
            copy_original=False,
        )

        return ActionResult([result_item])
    else:
        config_result = tabbed_webpage_config(input)
        return tabbed_webpage_generate(
            ActionInput(items=config_result.items), add_title=not no_title
        )
