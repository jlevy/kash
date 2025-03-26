from pathlib import Path

from frontmatter_format import FmStyle, fmf_has_frontmatter, fmf_read, fmf_write
from funlog import tally_calls
from prettyfmt import custom_key_sort, fmt_size_human

from kash.config.logger import get_logger
from kash.model.items_model import ITEM_FIELDS, Item
from kash.model.operations_model import OPERATION_FIELDS
from kash.text_handling.doc_normalization import normalize_formatting_ansi
from kash.utils.common.format_utils import fmt_loc
from kash.utils.file_utils.file_formats_model import Format
from kash.utils.file_utils.mtime_cache import MtimeCache

log = get_logger(__name__)

# Keeps YAML much prettier.
ITEM_FIELD_SORT = custom_key_sort(OPERATION_FIELDS + ITEM_FIELDS)

# Initialize the file modification time cache with Item type
_item_cache = MtimeCache[Item](max_size=2000, name="Item")


@tally_calls()
def write_item(item: Item, path: Path):
    """
    Write a text item to a file with standard frontmatter format YAML.
    Also normalizes formatting of the body text.
    """
    item.validate()
    if item.is_binary:
        raise ValueError(f"Binary items should be external files: {item}")
    if item.format and not item.format.supports_frontmatter:
        raise ValueError(f"Item format `{item.format.value}` does not support frontmatter: {item}")

    # Clear cache before writing.
    _item_cache.delete(path)

    body = normalize_formatting_ansi(item.body_text(), item.format)

    # Special case for YAML files to avoid a possible duplicate `---` divider in the body.
    if body and item.format == Format.yaml:
        stripped = body.lstrip()
        if stripped.startswith("---\n"):
            body = stripped[4:]

    # Decide on the frontmatter style.
    format = Format(item.format)
    if format == Format.html:
        fm_style = FmStyle.html
    elif format in [Format.python, Format.kash_script, Format.diff, Format.csv, Format.log]:
        fm_style = FmStyle.hash
    elif format == Format.json:
        fm_style = FmStyle.slash
    else:
        fm_style = FmStyle.yaml

    log.debug("Writing item to %s: body length %s, metadata %s", path, len(body), item.metadata())

    fmf_write(
        path,
        body,
        item.metadata(),
        style=fm_style,
        key_sort=ITEM_FIELD_SORT,
        make_parents=True,
    )

    # Update cache.
    _item_cache.update(path, item)


def read_item(path: Path, base_dir: Path | None) -> Item:
    """
    Read an item from a file. Uses `base_dir` to resolve paths, so the item's
    `store_path` will be set and be relative to `base_dir`.

    If frontmatter format YAML is present, it is parsed. If not, the item will
    be a resource with a format inferred from the file extension or the content.
    The `store_path` will be the path relative to the `base_dir`, if the file
    is within `base_dir`, or otherwise the `external_path` will be set to the path
    it was read from.
    """

    cached_item = _item_cache.read(path)
    if cached_item:
        log.debug("Cache hit for item: %s", path)
        return cached_item

    return _read_item_uncached(path, base_dir)


@tally_calls()
def _read_item_uncached(path: Path, base_dir: Path | None) -> Item:
    has_frontmatter = fmf_has_frontmatter(path)
    body = metadata = None
    if has_frontmatter:
        body, metadata = fmf_read(path)
        log.debug("Read item from %s: body length %s, metadata %s", path, len(body), metadata)

        path = path.resolve()
        if base_dir:
            base_dir = base_dir.resolve()

    # Ensure store_path is used if it's within the base_dir, and
    # external_path otherwise.
    if base_dir and path.is_relative_to(base_dir):
        store_path = str(path.relative_to(base_dir))
        external_path = None
    else:
        store_path = None
        external_path = str(path)

    if metadata:
        # We've read the file into memory.
        item = Item.from_dict(
            metadata, body=body, store_path=store_path, external_path=external_path
        )
    else:
        # This is a file without frontmatter. Infer format from the file and content,
        # and use store_path or external_path as appropriate.
        item = Item.from_external_path(path)
        if item.format:
            log.info(
                "Metadata not present on text file, inferred format `%s`: %s",
                item.format.value,
                fmt_loc(path),
            )
        item.store_path = store_path
        item.original_filename = path.name
        if not item.format or item.format.is_binary:
            item.body = None
            item.external_path = external_path
        else:
            stat = path.stat()
            if stat.st_size > 100 * 1024 * 1024:
                log.warning(
                    "Reading large text file (%s) into memory: %s",
                    fmt_size_human(stat.st_size),
                    fmt_loc(path),
                )
            with open(path, encoding="utf-8") as f:
                item.body = f.read()
            item.external_path = None

    # Update modified time.
    item.set_modified(path.stat().st_mtime)

    # Update the cache with the new item
    _item_cache.update(path, item)

    return item
