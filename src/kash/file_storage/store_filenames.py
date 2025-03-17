from pathlib import Path

from kash.config.logger import get_logger
from kash.model.items_model import ItemType
from kash.utils.file_utils.file_formats_model import FileExt, Format
from kash.utils.file_utils.filename_parsing import split_filename
from kash.utils.lang_utils.inflection import plural

log = get_logger(__name__)


_type_to_folder = {name: plural(name) for name, _value in ItemType.__members__.items()}


def folder_for_type(item_type: ItemType) -> Path:
    """
    Relative Path for the folder containing this item type.

    doc -> docs
    resource -> resources
    config -> configs
    export -> exports
    etc.
    """
    return Path(_type_to_folder[item_type.name])


def join_suffix(base_slug: str, full_suffix: str) -> str:
    return f"{base_slug}.{full_suffix.lstrip('.')}"


def parse_item_filename(
    path: str | Path,
) -> tuple[str, ItemType | None, Format | None, FileExt | None]:
    """
    Parse a store file path into its name, format, and extension. Returns None for
    format or item type if not recognized. Raises `InvalidFilename` if the file extension
    is not recognized, since we expect all store files to have a recognized extension.
    """
    path_str = str(path)
    _dirname, name, item_type_str, ext_str = split_filename(path_str)
    file_ext = FileExt.parse(ext_str)
    format = Format.guess_by_file_ext(file_ext) if file_ext else None

    # TODO: For yaml file resources, look at the format in the metadata.

    item_type = None
    if item_type_str:
        try:
            item_type = ItemType(item_type_str)
        except ValueError:
            pass
    return name, item_type, format, file_ext
