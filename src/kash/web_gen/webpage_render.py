from __future__ import annotations

from chopdiff.html import rewrite_html_img_urls
from sidematter_format import Sidematter, copy_sidematter

from kash.config.logger import get_logger
from kash.model.items_model import Item
from kash.utils.file_utils.file_formats_model import Format
from kash.utils.text_handling.markdown_utils import rewrite_image_urls
from kash.web_gen.template_render import render_web_template
from kash.workspaces.workspaces import current_ws

log = get_logger(__name__)


def copy_item_sidematter(
    input_item: Item,
    result_item: Item,
) -> tuple[str, str]:
    """
    Copy the sidematter of an item to a new item. Useful for copying assets, especially images.
    """
    ws = current_ws()

    # Manually copy over metadata and assets. This makes image assets work.
    assert input_item.store_path
    src_path = ws.base_dir / input_item.store_path
    dest_path = ws.assign_store_path(result_item)

    log.message(
        "Copying sidematter and assets: %s -> %s",
        input_item.store_path,
        result_item.store_path,
    )
    copy_sidematter(
        src_path=src_path,
        dest_path=dest_path,
        make_parents=True,
        copy_original=False,
    )

    old_prefix = Sidematter(src_path).assets_dir.name
    new_prefix = Sidematter(dest_path).assets_dir.name

    return old_prefix, new_prefix


def rewrite_item_image_urls(
    input_item: Item,
    old_prefix: str,
    new_prefix: str,
) -> Item:
    """
    Rewrite image path prefixes. Useful when we are rendering an item with sidematter
    asset paths.
    """

    # Rewrite image paths to be relative to the workspace.
    assert input_item.body
    if input_item.format in (Format.markdown, Format.md_html):
        rewritten_body = rewrite_image_urls(input_item.body, old_prefix, new_prefix)
    elif input_item.format == Format.html:
        rewritten_body = rewrite_html_img_urls(
            input_item.body, from_prefix=old_prefix, to_prefix=new_prefix
        )
    else:
        rewritten_body = input_item.body

    change_str = "found" if rewritten_body != input_item.body else "none found"
    log.message("Rewrote doc image paths (%s): `%s` -> `%s`", change_str, old_prefix, new_prefix)
    rewritten_item = input_item.derived_copy(body=rewritten_body)

    return rewritten_item


def render_item_as_html(
    input_item: Item,
    result_item: Item,
    *,
    add_title_h1: bool,
    template_filename: str = "youtube_webpage.html.jinja",
) -> Item:
    """
    Render an item as HTML, including copying sidematter and assets.
    Also rewrites image paths to be relative to the workspace.
    The partly filled-in result item is needed to be able to assign a store path.
    If `add_title_h1` is True, the title will be inserted as an h1 heading above the body.
    """

    old_prefix, new_prefix = copy_item_sidematter(input_item, result_item)

    rewritten_item = rewrite_item_image_urls(input_item, old_prefix, new_prefix)

    result_item.body = render_web_template(
        template_filename=template_filename,
        data={
            "title": input_item.pick_title(),
            "add_title_h1": add_title_h1,
            "content_html": rewritten_item.body_as_html(),
            "thumbnail_url": input_item.thumbnail_url,
            "enable_themes": True,
            "show_theme_toggle": True,
        },
    )
    return result_item
