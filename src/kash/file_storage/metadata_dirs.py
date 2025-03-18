"""
Layout of the metadata files and directories with the file store.
"""

from pathlib import Path

from pydantic.dataclasses import dataclass

from kash.config.logger import get_logger
from kash.config.settings import CONTENT_CACHE_NAME, DOT_DIR, MEDIA_CACHE_NAME
from kash.file_storage.persisted_yaml import PersistedYaml
from kash.model.paths_model import StorePath
from kash.utils.common.format_utils import fmt_loc
from kash.utils.file_utils.ignore_files import write_ignore

log = get_logger(__name__)


# Store format versioning, to allow warnings or checks as this format evolves.
# sv1: Initial version.
STORE_VERSION = "sv1"


@dataclass(frozen=True)
class MetadataDirs:
    base_dir: Path

    # All other paths are relative to the base directory so defaults are
    # always the same and can be set here:

    dot_dir: StorePath = StorePath(DOT_DIR)

    metadata_yml: StorePath = StorePath(f"{DOT_DIR}/metadata.yml")

    archive_dir: StorePath = StorePath(f"{DOT_DIR}/archive")

    settings_dir: StorePath = StorePath(f"{DOT_DIR}/settings")
    selection_yml: StorePath = StorePath(f"{DOT_DIR}/settings/selection.yml")
    params_yml: StorePath = StorePath(f"{DOT_DIR}/settings/params.yml")
    ignore_file: StorePath = StorePath(f"{DOT_DIR}/ignore")

    # Note cache location is also in global settings so might override these,
    # but usually global settings are the same as the paths here.
    cache_dir: StorePath = StorePath(f"{DOT_DIR}/cache")
    media_cache_dir: StorePath = StorePath(f"{DOT_DIR}/cache/{MEDIA_CACHE_NAME}")
    content_cache_dir: StorePath = StorePath(f"{DOT_DIR}/cache/{CONTENT_CACHE_NAME}")

    index_dir: StorePath = StorePath(f"{DOT_DIR}/index")

    history_dir: StorePath = StorePath(f"{DOT_DIR}/history")
    shell_history_yml: StorePath = StorePath(f"{DOT_DIR}/history/shell_history.yml")
    assistant_history_yml: StorePath = StorePath(f"{DOT_DIR}/history/assistant_history.yml")

    tmp_dir: StorePath = StorePath(f"{DOT_DIR}/tmp")

    def is_initialized(self):
        return (self.base_dir / self.metadata_yml).is_file()

    def initialize(self):
        """
        Create the directory and all metadata subdirectories and metadata file.
        Idempotent.
        """
        (self.base_dir / self.dot_dir).mkdir(parents=True, exist_ok=True)

        # Initialize metadata file.
        metadata_path = self.base_dir / self.metadata_yml
        if not metadata_path.exists():
            log.info("Initializing new store metadata: %s", fmt_loc(metadata_path))
        metadata = PersistedYaml(metadata_path, init_value={"store_version": STORE_VERSION})

        if metadata.read().get("store_version") != STORE_VERSION:
            log.warning(
                "Store metadata is version %r but we are using version %r: %s",
                metadata.read().get("store_version"),
                STORE_VERSION,
                fmt_loc(self.metadata_yml),
            )

        # Create directories.
        for field in self.__dataclass_fields__:
            dir_path = self.base_dir / getattr(self, field)
            if field.endswith("_dir"):
                dir_path.mkdir(parents=True, exist_ok=True)

        # Add a default ignore file if it doesn't exist.
        ignore_path = self.base_dir / self.ignore_file
        if not ignore_path.exists():
            write_ignore(ignore_path)
