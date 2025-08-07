from prettyfmt import fmt_lines
from sidematter_format import Sidematter

from kash.config.logger import get_logger
from kash.exec import kash_action
from kash.exec_model.args_model import ONE_OR_MORE_ARGS
from kash.model.actions_model import ActionInput, ActionResult
from kash.workspaces.workspaces import current_ws

log = get_logger(__name__)


@kash_action(expected_args=ONE_OR_MORE_ARGS)
def save_sidematter_meta(input: ActionInput) -> ActionResult:
    """
    Write the item's metadata as a [sidematter format](https://github.com/jlevy/sidematter-format)
    as `.meta.yml` and `.meta.json` files.

    If additional data items are provided, their data is merged into the primary item's metadata.
    This is useful for link data etc.
    """
    items = input.items
    assert items

    primary = items[0]
    assert primary.store_path

    ws = current_ws()
    sm = Sidematter(ws.base_dir / primary.store_path)

    metadata_dict = primary.metadata()

    for item in items[1:]:
        assert item.store_path
        metadata_dict = metadata_dict | item.read_as_data()

    # Write both JSON and YAML sidematter metadata
    sm.write_meta(metadata_dict, formats="all", make_parents=True)

    log.message(
        "Wrote sidematter metadata:\n%s",
        fmt_lines(
            [sm.meta_json_path.relative_to(ws.base_dir), sm.meta_yaml_path.relative_to(ws.base_dir)]
        ),
    )

    return ActionResult(items=[primary])
