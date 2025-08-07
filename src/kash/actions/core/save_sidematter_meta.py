from prettyfmt import fmt_lines
from sidematter_format import Sidematter

from kash.config.logger import get_logger
from kash.exec import kash_action
from kash.model import Item
from kash.workspaces.workspaces import current_ws

log = get_logger(__name__)


@kash_action()
def save_sidematter_meta(item: Item) -> Item:
    """
    Write the item's metadata as a [sidematter format](https://github.com/jlevy/sidematter-format)
    as `.meta.yml` and `.meta.json` files.
    """
    assert item.store_path
    ws = current_ws()
    sm = Sidematter(ws.base_dir / item.store_path)

    metadata_dict = item.metadata()

    # Write both JSON and YAML sidematter metadata
    sm.write_meta(metadata_dict, formats="all", make_parents=True)

    log.message(
        "Wrote sidematter metadata:\n%s",
        fmt_lines(
            [sm.meta_json_path.relative_to(ws.base_dir), sm.meta_yaml_path.relative_to(ws.base_dir)]
        ),
    )

    return item
