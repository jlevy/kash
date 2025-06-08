from kash.exec import kash_action
from kash.exec.preconditions import has_fullpage_html_body
from kash.model import Format, Item, Param
from kash.utils.errors import InvalidInput
from kash.workspaces.workspaces import current_ws


@kash_action(
    precondition=has_fullpage_html_body,
    params=(
        Param("no_js_min", "Disable JS minification", bool),
        Param("no_css_min", "Disable CSS minification", bool),
    ),
)
def minify_html(item: Item) -> Item:
    """
    Minify an HTML item's content using [html-minifier-terser](https://github.com/terser/html-minifier-terser).

    Also supports Tailwind CSS v4 compilation and inlining, if any Tailwind
    CSS v4 CDN script tags are found.

    The terser minification seems a bit slower but more robust than
    [minify-html](https://github.com/wilsonzlin/minify-html).
    """
    from minify_tw_html import minify_tw_html

    if not item.store_path:
        raise InvalidInput(f"Missing store path: {item}")

    ws = current_ws()
    input_path = ws.base_dir / item.store_path

    output_item = item.derived_copy(format=Format.html)
    output_path = ws.target_path_for(output_item)

    minify_tw_html(input_path, output_path)

    # Indicate item is already saved.
    output_item.external_path = str(output_path)

    return output_item
