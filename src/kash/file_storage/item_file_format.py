from pathlib import Path

from frontmatter_format import (
    FmStyle,
    fmf_has_frontmatter,
    fmf_read,
    fmf_read_frontmatter,
    fmf_write,
)
from funlog import tally_calls
from prettyfmt import custom_key_sort, fmt_size_human
from sidematter_format import Sidematter
from strif import atomic_output_file, single_line

from kash.config.logger import get_logger
from kash.model.items_model import ITEM_FIELDS, Item
from kash.model.operations_model import OPERATION_FIELDS
from kash.utils.common.format_utils import fmt_loc
from kash.utils.file_utils.file_formats_model import Format
from kash.utils.file_utils.mtime_cache import MtimeCache
from kash.utils.text_handling.doc_normalization import normalize_formatting

log = get_logger(__name__)

# Keeps YAML much prettier.
ITEM_FIELD_SORT = custom_key_sort(OPERATION_FIELDS + ITEM_FIELDS)

# Initialize the file modification time cache with Item type
_item_cache = MtimeCache[Item](max_size=2000, name="Item")


@tally_calls()
def write_item(item: Item, path: Path, *, normalize: bool = True, use_frontmatter: bool = True):
    """
    Write a text item to a file with standard frontmatter format YAML or sidematter format.
    By default normalizes formatting of the body text and updates the item's body.

    If `use_frontmatter` is True, uses frontmatter on the file for metadata, and omits
    the sidematter metadata file.

    This function does not explicitly write sidematter assets; these can be written
    separately.
    """
    item.validate()
    if use_frontmatter and item.format and not item.format.supports_frontmatter:
        raise ValueError(f"Item format `{item.format.value}` does not support frontmatter: {item}")

    # Clear cache before writing.
    _item_cache.delete(path)

    title = item.title
    if normalize:
        if item.title:
            title = single_line(item.title)
        body = normalize_formatting(item.body_text(), item.format)
    else:
        body = item.body_text()

    # Special case for YAML files to avoid a possible duplicate `---` divider in the body.
    if body and item.format == Format.yaml:
        stripped = body.lstrip()
        if stripped.startswith("---\n"):
            body = stripped[4:]

    # Decide on the frontmatter style.
    format = Format(item.format)
    if format == Format.html:
        fm_style = FmStyle.html
    elif format in [
        Format.python,
        Format.shellscript,
        Format.xonsh,
        Format.diff,
        Format.csv,
        Format.log,
    ]:
        fm_style = FmStyle.hash
    elif format == Format.json:
        fm_style = FmStyle.slash
    else:
        fm_style = FmStyle.yaml

    log.debug("Writing item to %s: body length %s, metadata %s", path, len(body), item.metadata())

    # Use sidematter format
    spath = Sidematter(path)
    if use_frontmatter:
        # Use frontmatter format
        fmf_write(
            path,
            body,
            item.metadata(),
            style=fm_style,
            key_sort=ITEM_FIELD_SORT,
            make_parents=True,
        )
    else:
        # Write the main file with just the body (no frontmatter)
        with atomic_output_file(path, make_parents=True) as f:
            f.write_text(body, encoding="utf-8")

        # Sidematter metadata
        spath.write_meta(item.metadata(), key_sort=ITEM_FIELD_SORT)

    # Update cache.
    _item_cache.update(path, item)

    # Update the item.
    item.title = title
    item.body = body


def read_item(path: Path, base_dir: Path | None, preserve_filename: bool = True) -> Item:
    """
    Read a text item from a file. Uses `base_dir` to resolve paths, so the item's
    `store_path` will be set and be relative to `base_dir`.

    Automatically detects and reads sidematter format (metadata in .meta.yml/.meta.json
    sidecar files), which takes precedence over frontmatter when present. Falls back to
    frontmatter format YAML if no sidematter is found. If neither is present, the item
    will be a resource with a format inferred from the file extension or the content.

    The `store_path` will be the path relative to the `base_dir`, if the file
    is within `base_dir`, or otherwise the `external_path` will be set to the path
    it was read from.
    """

    cached_item = _item_cache.read(path)
    if cached_item:
        log.debug("Cache hit for item: %s", path)
        return cached_item

    return _read_item_uncached(path, base_dir, preserve_filename=preserve_filename)


@tally_calls()
def _read_item_uncached(
    path: Path,
    base_dir: Path | None,
    *,
    preserve_filename: bool = True,
    prefer_frontmatter: bool = True,
) -> Item:
    # First, try to resolve sidematter
    sidematter = Sidematter(path).resolve(use_frontmatter=False)

    # Use sidematter metadata unless we find and prefer frontmatter for metadata.
    has_frontmatter = fmf_has_frontmatter(path)
    frontmatter_meta = prefer_frontmatter and has_frontmatter and fmf_read_frontmatter(path)
    if sidematter.meta and not frontmatter_meta:
        metadata = sidematter.meta
        body, _frontmatter_metadata = fmf_read(path)
        log.debug(
            "Read item from sidematter %s: body length %s, metadata %s",
            sidematter.meta_path,
            len(body),
            metadata,
        )
    elif has_frontmatter:
        body, metadata = fmf_read(path)
        log.debug(
            "Read item from %s: body length %s, metadata %s",
            path,
            len(body),
            metadata,
        )
    else:
        # Not readable, binary or otherwise.
        metadata = None
        body = None

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
        # This is a file without frontmatter or sidematter.
        # Infer format from the file and content,
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

    # Preserve the original filename.
    if preserve_filename:
        item.original_filename = path.name

    # Update modified time.
    item.set_modified(path.stat().st_mtime)

    # Update the cache with the new item
    _item_cache.update(path, item)

    return item
