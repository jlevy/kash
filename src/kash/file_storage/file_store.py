import functools
import os
import shutil
import threading
import time
from collections.abc import Callable, Generator
from os.path import join, relpath
from pathlib import Path
from typing import Concatenate, ParamSpec, TypeVar

from funlog import format_duration, log_calls
from prettyfmt import fmt_lines, fmt_path
from sidematter_format import copy_sidematter, move_sidematter, remove_sidematter
from strif import copyfile_atomic, hash_file
from typing_extensions import override

from kash.config.logger import get_log_settings, get_logger
from kash.config.text_styles import EMOJI_SAVED
from kash.file_storage.item_id_index import ItemIdIndex
from kash.file_storage.metadata_dirs import MetadataDirs
from kash.file_storage.store_filenames import folder_for_type, join_suffix
from kash.model.items_model import Item, ItemType
from kash.model.paths_model import StorePath
from kash.shell.output.shell_output import PrintHooks
from kash.utils.common.format_utils import fmt_loc
from kash.utils.common.url import Locator, UnresolvedLocator, Url, is_url
from kash.utils.errors import FileExists, FileNotFound
from kash.utils.file_utils.file_formats_model import Format
from kash.utils.file_utils.file_walk import walk_by_dir
from kash.utils.file_utils.ignore_files import IgnoreChecker, add_to_ignore
from kash.workspaces import SelectionHistory
from kash.workspaces.param_state import ParamState
from kash.workspaces.workspaces import Workspace

log = get_logger(__name__)


SelfT = TypeVar("SelfT")
T = TypeVar("T")
P = ParamSpec("P")


def synchronized(
    method: Callable[Concatenate[SelfT, P], T],
) -> Callable[Concatenate[SelfT, P], T]:
    """
    Simple way to synchronize a few methods.
    """

    @functools.wraps(method)
    def synchronized_method(self, *args: P.args, **kwargs: P.kwargs) -> T:
        with self._lock:
            return method(self, *args, **kwargs)

    return synchronized_method


class FileStore(Workspace):
    """
    The main class to manage files in a workspace, holding settings and files with items.
    Thread safe since file operations are atomic and mutable state is synchronized.
    """

    # TODO: Consider using a pluggable filesystem (fsspec AbstractFileSystem).

    def __init__(self, base_dir: Path, is_global_ws: bool, auto_init: bool = True):
        """
        Load the file store. With `auto_init` true, will initialize if the workspace
        directory metadata if it is not already initialized.
        """

        self.base_dir_path = base_dir.resolve()
        self.name = self.base_dir_path.name
        self.is_global_ws = is_global_ws
        self._lock = threading.RLock()
        self.reload(auto_init=auto_init)

    @property
    @override
    def base_dir(self) -> Path:
        return self.base_dir_path

    @synchronized
    @log_calls(level="warning", if_slower_than=2.0)
    def reload(self, auto_init: bool = True):
        """
        Load or reload all state.
        """
        self.start_time = time.time()
        self.info_logged = False
        self.warnings: list[str] = []

        # Index of item identifiers and unique slug history
        self.id_index = ItemIdIndex()

        self.dirs = MetadataDirs(base_dir=self.base_dir, is_global_ws=self.is_global_ws)
        if not auto_init and not self.dirs.is_initialized():
            raise FileNotFound(f"Directory is not a file store workspace: {self.base_dir}")

        self.dirs.initialize()

        add_to_ignore(self.base_dir / ".gitignore", [".kash/"])

        # Initialize selection with history support.
        self.selections = SelectionHistory.init(self.base_dir / self.dirs.selection_yml)

        # Initialize ignore checker.
        self.is_ignored = IgnoreChecker.from_file(self.base_dir / self.dirs.ignore_file)

        self._id_index_init()

        # Filter out any non-existent paths from the initial selection.
        if self.selections.history:
            self._filter_selection_paths()

        self.params = ParamState(self.base_dir / self.dirs.params_yml)

        self.end_time = time.time()

        # Warm the item cache in a separate thread.
        from kash.file_storage.store_cache_warmer import warm_file_store

        warm_file_store(self)

    def __str__(self):
        return f"FileStore(~{self.name})"

    def _id_index_init(self):
        num_dups = 0
        for store_path in self.walk_items():
            dup_path = self.id_index.index_item(store_path, self.load)
            if dup_path:
                num_dups += 1

        if num_dups > 0:
            self.warnings.append(
                f"Found {num_dups} duplicate items in store. See `logs` for details."
            )

    def resolve_to_store_path(self, path: Path | StorePath) -> StorePath | None:
        """
        Return a StorePath if the given path is within the store, otherwise None.
        If it is already a StorePath, return it unchanged.
        """
        if isinstance(path, StorePath):
            return path
        resolved = path.resolve()
        if resolved.is_relative_to(self.base_dir):
            return StorePath(resolved.relative_to(self.base_dir))
        else:
            return None

    def resolve_to_abs_path(self, path: Path | StorePath) -> Path:
        """
        Return an absolute path, resolving any store paths to within the store
        and resolving other paths like regular `Path.resolve()`.
        """
        store_path = self.resolve_to_store_path(path)
        if store_path:
            return self.base_dir / store_path
        elif path.is_absolute():
            return path
        else:
            # Unspecified relative paths resolved to cwd.
            # TODO: Consider if such paths might be store paths.
            return path.resolve()

    def exists(self, store_path: StorePath) -> bool:
        """
        Check given store path refers to an existing file.
        """
        return (self.base_dir / store_path).exists()

    def _pick_filename_for(self, item: Item, *, overwrite: bool = False) -> tuple[str, str | None]:
        """
        Get a suitable filename for this item. If `overwrite` is true, use the the slugified
        title, regardless of whether it is already in the store.
        If `overwrite` is false, use the slugified title with a suffix to make it unique
        (and in this case also return the old filename for this item).
        """
        if overwrite:
            log.info(
                "Picked default filename: %s for item: %s",
                item.default_filename(),
                item,
            )
            return item.default_filename(), None

        slug = item.slug_name()
        full_suffix = item.get_full_suffix()
        # Get a unique name per item type.
        unique_slug, old_slugs = self.id_index.uniquify_slug(slug, full_suffix)

        # Suffix files with both item type and a suitable file extension.
        new_unique_filename = join_suffix(unique_slug, full_suffix)

        old_filename = join_suffix(old_slugs[0], full_suffix) if old_slugs else None

        log.info("Picked new unique filename: %s for item: %s", new_unique_filename, item)
        return new_unique_filename, old_filename

    def default_path_for(self, item: Item) -> StorePath:
        """
        Get the default store path for an item based on slugifying its title or other metadata.
        """
        folder_path = folder_for_type(item.type)
        return StorePath(folder_path / item.default_filename())

    @synchronized
    def find_by_id(self, item: Item) -> StorePath | None:
        """
        Best effort to see if an item with the same identity is already in the store.
        """
        item_id = item.item_id()
        log.info("Looking for item by id:\n%s", fmt_lines([item, item_id]))
        if not item_id:
            return None
        else:
            store_path = self.id_index.find_store_path_by_id(item_id)
            if not store_path:
                # Just in case the index is not complete, check the other paths too
                possible_paths = [
                    p
                    for p in [
                        item.store_path,
                        self.store_path_for(item)[0],
                        self.default_path_for(item),
                    ]
                    if p
                ]
                for p in possible_paths:
                    if self.exists(p):
                        old_item = self.load(p)
                        if old_item.item_id() == item_id:
                            log.info(
                                "Item with the same id already saved (disk check):\n%s",
                                fmt_lines([fmt_loc(p), item_id]),
                            )
                            # Ensure index is updated consistently and with logging
                            self.id_index.index_item(p, self.load)
                            return p
                log.info("Also checked paths but no id match:\n%s", fmt_lines(possible_paths))
            if store_path and self.exists(store_path):
                log.info(
                    "Item with the same id already saved (disk check):\n%s",
                    fmt_lines([fmt_loc(store_path), item_id]),
                )
                return store_path
        return None

    @synchronized
    def store_path_for(
        self, item: Item, *, as_tmp: bool = False, overwrite: bool = False
    ) -> tuple[StorePath, StorePath | None]:
        """
        Return the store path for an item. If the item already has a `store_path`, we use that.
        Otherwise we need to find the store path or generate a new one that seems suitable.

        Returns `store_path, old_store_path` where `old_store_path` is the previous similarly
        named item with a different identity (or None there is none).

        If `as_tmp` is true, will return a path from the temporary directory in the store.
        Normally an item is always saved to a unique store path but if `overwrite` is true,
        will always save to the same path
        """
        item_id = item.item_id()
        old_filename = None
        if as_tmp:
            return self._tmp_path_for(item), None
        elif item.store_path:
            return StorePath(item.store_path), None
        elif (
            item_id
            and (existing := self.id_index.find_store_path_by_id(item_id))
            and self.exists(existing)
        ):
            # If this item has an identity and we've saved under that id before, use the same store path.
            store_path = existing
            log.info(
                "When picking a store path, found an existing item with same id:\n%s",
                fmt_lines([fmt_loc(store_path), item_id]),
            )
            return store_path, None
        else:
            # We need to pick the path and filename.
            folder_path = folder_for_type(item.type)
            filename, old_filename = self._pick_filename_for(item, overwrite=overwrite)
            store_path = folder_path / filename

            old_store_path = None
            if old_filename and Path(self.base_dir / folder_path / old_filename).exists():
                old_store_path = StorePath(folder_path / old_filename)

            return StorePath(store_path), old_store_path

    @synchronized
    def assign_store_path(self, item: Item) -> Path:
        """
        Pick a new store path for the item and mutate `item.store_path`.

        This is useful if you need to write to the store yourself, at the location
        the item usually would be saved, and also want the path to be fixed.

        This is idempotent. If you also write to the file, call `mark_as_saved()`
        to indicate that the file is now saved. Otherwise the item should be saved
        with `save()`.

        Returns the absolute path, for convenience if you wish to write to the file
        directly.
        """
        store_path, _old_store_path = self.store_path_for(item)
        item.store_path = str(store_path)
        return self.base_dir / store_path

    def _tmp_path_for(self, item: Item) -> StorePath:
        """
        Find a path for an item in the tmp directory.
        """
        if not item.store_path:
            store_path, _old = self.store_path_for(item, as_tmp=False)
            return StorePath(self.dirs.tmp_dir / store_path)
        elif (self.base_dir / item.store_path).is_relative_to(self.dirs.tmp_dir):
            return StorePath(item.store_path)
        else:
            return StorePath(self.dirs.tmp_dir / item.store_path)

    def _is_in_store(self, path: Path) -> bool:
        path = path.resolve()
        return path.is_relative_to(self.base_dir) and not path.is_relative_to(
            self.base_dir / self.dirs.dot_dir
        )

    @log_calls()
    def save(
        self,
        item: Item,
        *,
        overwrite: bool = False,
        as_tmp: bool = False,
        no_format: bool = False,
        no_frontmatter: bool = False,
    ) -> StorePath:
        """
        Save the item. Uses the `store_path` if it's already set or generates a new one.
        Updates `item.store_path`. An existing file can be added by having the item's
        `external_path` set to a location (inside or outside the store).

        Unless `no_format` is true, also normalizes body text formatting (for Markdown)
        and updates the item's body to match.

        If `no_frontmatter` is true, will not add frontmatter metadata to the item.

        If `overwrite` is true, will overwrite a file that has the same path.

        If `as_tmp` is true, will save the item to a temporary file.
        """
        if overwrite and as_tmp:
            raise ValueError("Cannot both overwrite and save to a temporary file.")

        # If external path already exists and is within the workspace, the file was
        # already saved (e.g. by an action that wrote the item directly to the store).
        external_path = item.external_path and Path(item.external_path).resolve()
        skipped_save = False
        if external_path and self._is_in_store(external_path):
            log.info("Item with external_path already saved: %s", fmt_loc(external_path))
            rel_path = external_path.relative_to(self.base_dir)
            # Indicate this is an item with a store path, not an external path.
            # Keep external_path set so we know body is in that file.
            item.store_path = str(rel_path)
            # Ensure index is updated for items written directly into the store.
            self.id_index.index_item(StorePath(rel_path), self.load)
            return StorePath(rel_path)
        else:
            # Otherwise it's still in memory or in a file outside the workspace and we need to save it.
            store_path, old_store_path = self.store_path_for(
                item, as_tmp=as_tmp, overwrite=overwrite
            )

            full_path = self.base_dir / store_path

            supports_frontmatter = item.format and item.format.supports_frontmatter
            log.info(
                "Saving item in format %s (supports_frontmatter=%s) to %s: %s",
                item.format,
                supports_frontmatter,
                fmt_loc(full_path),
                item,
            )

            # If we're overwriting an existing file, archive it first so it is in the archive, not lost.
            if full_path.exists():
                try:
                    log.info(
                        "Previous file exists so will archive it: %s",
                        fmt_loc(store_path),
                    )
                    self.archive(store_path, quiet=True)
                except Exception as e:
                    log.info("Exception archiving existing file: %s", e)

            # Now save the new item.
            try:
                # For binary or unknown formats or if we're not adding frontmatter, copy the file.
                if item.external_path and (no_frontmatter or not supports_frontmatter):
                    log.info(
                        "Path is an external path, so copying: %s -> %s",
                        fmt_path(item.external_path),
                        fmt_path(full_path),
                    )
                    copyfile_atomic(item.external_path, full_path, make_parents=True)
                else:
                    # Save as a text item with frontmatter.
                    if item.external_path:
                        item.body = Path(item.external_path).read_text()
                    from kash.file_storage.item_file_format import write_item

                    write_item(item, full_path, normalize=not no_format)
            except OSError as e:
                log.error("Error saving item: %s", e)
                try:
                    self.unarchive(store_path)
                except Exception:
                    pass
                raise e

            # Set filesystem file creation and modification times as well.
            if item.created_at:
                created_time = item.created_at.timestamp()
                modified_time = item.modified_at.timestamp() if item.modified_at else created_time
                os.utime(full_path, (modified_time, modified_time))

            # Check if it's an exact duplicate of the previous file, to reduce clutter.
            if old_store_path:
                old_item = self.load(old_store_path)
                new_item = self.load(store_path)  # Reload it to get normalized text.
                if new_item.content_equals(old_item):
                    log.message(
                        "New item is identical to previous version, will keep old item: %s",
                        fmt_loc(old_store_path),
                    )
                    os.unlink(full_path)
                    store_path = old_store_path
                    skipped_save = True

        # Update in-memory store_path only after successful save.
        item.store_path = str(store_path)
        self.id_index.index_item(store_path, self.load)

        if not skipped_save:
            log.message("%s Saved item: %s", EMOJI_SAVED, fmt_loc(store_path))
        else:
            log.info("%s Already saved: %s", EMOJI_SAVED, fmt_loc(store_path))

        return store_path

    @log_calls(level="debug")
    def load(self, store_path: StorePath) -> Item:
        """
        Load item at the given path.
        """
        from kash.file_storage.item_file_format import read_item

        return read_item(self.base_dir / store_path, self.base_dir)

    def hash(self, store_path: StorePath) -> str:
        """
        Get a hash of the item at the given path.
        """
        return hash_file(self.base_dir / store_path, algorithm="sha1").with_prefix

    def import_item(
        self,
        locator: UnresolvedLocator,
        *,
        as_type: ItemType | None = None,
        reimport: bool = False,
        with_sidematter: bool = False,
    ) -> StorePath:
        """
        Add resources from files or URLs. If a locator is a path, copy it into the store.
        Unless `reimport` is true, paths and (canonicalized) URLs already in the store
        are not imported again and the existing store path is returned.
        If `as_type` is specified, it will be used to override the item type, otherwise
        we go with our best guess.
        If `with_sidematter` is true, will copy any sidematter files (metadata/assets) to
        the destination.
        """
        from kash.file_storage.item_file_format import read_item
        from kash.web_content.canon_url import canonicalize_url

        if isinstance(locator, StorePath) and not reimport:
            log.info("Store path already imported: %s", fmt_loc(locator))
            self.id_index.index_item(locator, self.load)
            return locator
        elif is_url(locator):
            # Import a URL as a resource.
            orig_url = Url(str(locator))
            url = canonicalize_url(orig_url)
            if url != orig_url:
                log.message("Canonicalized URL: %s -> %s", orig_url, url)
            item_type = as_type or ItemType.resource
            item = Item(item_type, url=url, format=Format.url)
            previous_store_path = self.find_by_id(item)
            if previous_store_path and not reimport:
                log.info(
                    "Workspace already has this URL:\n%s",
                    fmt_lines([fmt_loc(previous_store_path), url]),
                )
                return previous_store_path
            else:
                store_path = self.save(item)
                return store_path
        else:
            # We have a path, possibly outside of or inside of the store.
            path = Path(locator).resolve()
            if path.is_relative_to(self.base_dir):
                store_path = StorePath(path.relative_to(self.base_dir))
                if self.exists(store_path) and not reimport:
                    log.message("Path already imported: %s", fmt_loc(store_path))
                    return store_path

            if not path.exists():
                raise FileNotFound(f"File not found: {fmt_loc(path)}")

            # First treat it as an external file to analyze file type and format.
            item = Item.from_external_path(path)

            # If it's a text/frontmatter-friendly, read it fully.
            if item.format and item.format.supports_frontmatter:
                log.message("Importing text file: %s", fmt_loc(path))
                # This will read the file with or without frontmatter.
                # We are importing so we want to drop the external path so we save the body.
                item = read_item(path, self.base_dir)
                item.external_path = None

                if item.type and as_type and item.type != as_type:
                    log.warning(
                        "Reimporting as item type `%s` instead of `%s`: %s",
                        as_type.value,
                        item.type.value,
                        fmt_loc(path),
                    )
                    item.type = as_type

                # This will only have a store path if it was already in the store; otherwise
                # we'll pick a new store path.
                store_path = self.save(item)
                log.info("Imported text file: %s", item.as_str())
                # If requested, also copy any sidematter files (metadata/assets) to match destination.
                if with_sidematter:
                    copy_sidematter(path, self.base_dir / store_path, copy_original=False)
            else:
                # Binary or other files we just copy over as-is, preserving the name.
                # We know the extension is recognized.
                store_path, old_store_path = self.store_path_for(item)
                if self.exists(store_path):
                    raise FileExists(f"Resource already in store: {fmt_loc(store_path)}")

                log.message("Importing resource: %s", fmt_loc(path))
                if with_sidematter:
                    copy_sidematter(path, self.base_dir / store_path)
                else:
                    copyfile_atomic(path, self.base_dir / store_path, make_parents=True)

                # Optimization: Don't import an identical file twice.
                if old_store_path:
                    old_hash = self.hash(old_store_path)
                    new_hash = self.hash(store_path)
                    if old_hash == new_hash:
                        log.message(
                            "Imported resource is identical to the previous import: %s",
                            fmt_loc(old_store_path),
                        )
                        if with_sidematter:
                            remove_sidematter(self.base_dir / store_path)
                        else:
                            os.unlink(self.base_dir / store_path)
                        store_path = old_store_path
                log.message("Imported resource: %s", fmt_loc(store_path))
            return store_path

    def import_items(
        self,
        *locators: Locator,
        as_type: ItemType | None = None,
        reimport: bool = False,
        with_sidematter: bool = False,
    ) -> list[StorePath]:
        return [
            self.import_item(
                locator, as_type=as_type, reimport=reimport, with_sidematter=with_sidematter
            )
            for locator in locators
        ]

    def import_and_load(self, locator: UnresolvedLocator, with_sidematter: bool = False) -> Item:
        """
        Import a locator and return the item.
        """
        store_path = self.import_item(locator, with_sidematter=with_sidematter)
        return self.load(store_path)

    def _filter_selection_paths(self):
        """
        Filter out any paths that don't exist from all selections.
        """
        non_existent = set()
        for selection in reversed(self.selections.history):
            non_existent.update(p for p in selection.paths if not self.exists(p))

        if non_existent:
            log.warning(
                "Filtering out %s non-existent paths from selection history (%s selections, %s paths).",
                len(non_existent),
                len(self.selections.history),
                len(non_existent),
            )
        self.selections.remove_values(non_existent)

    @synchronized
    def _remove_references(self, store_paths: list[StorePath]):
        """
        Remove references to store_paths from selections and id index.
        """
        self.selections.remove_values(store_paths)
        for store_path in store_paths:
            self.id_index.unindex_item(store_path, self.load)
        # TODO: Update metadata of all relations that point to this path too.

    @synchronized
    def _rename_items(self, replacements: list[tuple[StorePath, StorePath]]):
        """
        Update references when items are renamed.
        """
        self.selections.replace_values(replacements)
        for store_path, new_store_path in replacements:
            self.id_index.unindex_item(store_path, self.load)
            self.id_index.index_item(new_store_path, self.load)
        # TODO: Update metadata of all relations that point to this path too.

    def archive(
        self,
        store_path: StorePath,
        *,
        missing_ok: bool = False,
        quiet: bool = False,
        with_sidematter: bool = False,
    ) -> StorePath:
        """
        Archive the item by moving it into the archive directory.
        """
        if not quiet:
            log.message(
                "Archiving item: %s -> %s/",
                fmt_loc(store_path),
                fmt_loc(self.dirs.archive_dir),
            )
        orig_path = self.base_dir / store_path
        full_archive_path = self.base_dir / self.dirs.archive_dir / store_path
        if missing_ok and not orig_path.exists():
            log.message("Item to archive not found so moving on: %s", fmt_loc(orig_path))
            return store_path
        if not orig_path.exists():
            log.warning("Item to archive not found: %s", fmt_loc(orig_path))
            return store_path
        # Remove references (including id_map) before moving so we can load the item to compute id.
        self._remove_references([store_path])
        if with_sidematter:
            move_sidematter(orig_path, full_archive_path)
        else:
            os.makedirs(full_archive_path.parent, exist_ok=True)
            shutil.move(orig_path, full_archive_path)

        archive_path = StorePath(self.dirs.archive_dir / store_path)
        return archive_path

    def unarchive(self, store_path: StorePath, with_sidematter: bool = False) -> StorePath:
        """
        Unarchive the item by moving back out of the archive directory.
        Path may be with or without the archive dir prefix.
        """
        full_input_path = (self.base_dir / store_path).resolve()
        full_archive_path = (self.base_dir / self.dirs.archive_dir).resolve()
        if full_input_path.is_relative_to(full_archive_path):
            store_path = StorePath(relpath(full_input_path, full_archive_path))
        original_path = self.base_dir / store_path
        if with_sidematter:
            move_sidematter(full_input_path, original_path)
        else:
            shutil.move(full_input_path, original_path)
        # Re-index after restoring from archive.
        self.id_index.index_item(store_path, self.load)
        return StorePath(store_path)

    @synchronized
    def log_workspace_info(self, *, once: bool = False) -> bool:
        """
        Log helpful information about the workspace.
        """
        if once and self.info_logged:
            return False

        self.info_logged = True

        PrintHooks.before_workspace_info()
        log.message(
            "Using workspace: %s (%s items)",
            fmt_path(self.base_dir, rel_to_cwd=False),
            len(self.id_index),
        )
        log.message(
            "Logging to: %s",
            fmt_path(get_log_settings().log_file_path.absolute(), rel_to_cwd=False),
        )
        log.message(
            "Caches: %s, %s",
            fmt_path(self.base_dir / self.dirs.media_cache_dir, rel_to_cwd=False),
            fmt_path(self.base_dir / self.dirs.content_cache_dir, rel_to_cwd=False),
        )
        log.message("Current working directory: %s", fmt_path(Path.cwd(), rel_to_cwd=False))

        for warning in self.warnings:
            log.warning("%s", warning)

        log.info(
            "File store startup took %s.",
            format_duration(self.end_time - self.start_time),
        )
        # TODO: Log more info like number of items by type.
        return True

    def walk_items(
        self,
        store_path: StorePath | None = None,
        *,
        use_ignore: bool = True,
    ) -> Generator[StorePath, None, None]:
        """
        Yields StorePaths of items in a folder or the entire store.
        """
        ignore = self.is_ignored if use_ignore else None

        start_path = self.base_dir / store_path if store_path else self.base_dir

        num_files = 0
        files_ignored = 0
        dirs_ignored = 0
        for flist in walk_by_dir(start_path, relative_to=self.base_dir, ignore=ignore):
            store_dirname = flist.parent_dir
            for filename in flist.filenames:
                yield StorePath(join(store_dirname, filename))
            num_files += flist.num_files
            files_ignored += flist.files_ignored
            dirs_ignored += flist.dirs_ignored

        log.info(
            "Walked %s files, ignoring %s files and %s directories.",
            num_files,
            files_ignored,
            dirs_ignored,
        )

    def normalize(
        self,
        store_path: StorePath,
        *,
        no_format: bool = False,
        no_frontmatter: bool = False,
    ) -> StorePath:
        """
        Normalize an item or all items in a folder to make sure contents are in current
        format. This is the same as loading and saving the item.
        """
        log.info("Normalizing item: %s", fmt_path(store_path))

        item = self.load(store_path)
        new_store_path = self.save(item, no_format=no_format, no_frontmatter=no_frontmatter)

        return new_store_path
