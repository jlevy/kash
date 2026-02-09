from __future__ import annotations

import zipfile

from sidematter_format import Sidematter

from kash.config.logger import get_logger
from kash.exec import kash_action
from kash.model.items_model import Item, ItemType
from kash.utils.file_utils.file_formats_model import Format
from kash.workspaces.workspaces import current_ws

log = get_logger(__name__)


@kash_action()
def zip_sidematter(item: Item) -> Item:
    """
    Zip all contents of the item, its sidematter metadata and items.
    """
    assert item.store_path
    ws = current_ws()
    sm = Sidematter(ws.base_dir / item.store_path)

    base_dir = sm.primary.parent

    # Collect all files to include; store paths relative to the primary's directory
    files_to_zip: list[tuple] = []

    files_to_zip.append((sm.primary, sm.primary.relative_to(base_dir)))
    if sm.meta_json_path.exists():
        files_to_zip.append((sm.meta_json_path, sm.meta_json_path.relative_to(base_dir)))
    if sm.meta_yaml_path.exists():
        files_to_zip.append((sm.meta_yaml_path, sm.meta_yaml_path.relative_to(base_dir)))
    if sm.assets_dir.exists():
        for p in sm.assets_dir.rglob("*"):
            if p.is_file():
                files_to_zip.append((p, p.relative_to(base_dir)))

    output_item = item.derived_copy(type=ItemType.export, format=Format.zip)
    target = ws.assign_store_path(output_item)

    with zipfile.ZipFile(
        target, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as zipf:
        for path, arcname in files_to_zip:
            zipf.write(path, arcname)

    return output_item
