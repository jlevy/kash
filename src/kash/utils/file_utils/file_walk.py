import os
from collections.abc import Generator
from dataclasses import dataclass
from os.path import abspath, relpath
from pathlib import Path

from kash.config.logger import get_logger
from kash.utils.common.format_utils import fmt_loc
from kash.utils.errors import FileNotFound
from kash.utils.file_utils.ignore_files import IgnoreFilter

log = get_logger(__name__)


@dataclass(frozen=True)
class FileList:
    """
    A flat list of files in a directory. It may also contain directories, if
    requested.
    """

    parent_dir: str
    filenames: list[str]
    dirnames: list[str] | None
    files_ignored: int
    dirs_ignored: int
    files_skipped: int
    dirs_skipped: int
    num_files: int  # Total number of files in the directory before capping


def walk_by_dir(
    start_path: Path,
    relative_to: Path,
    ignore: IgnoreFilter | None = None,
    max_depth: int = -1,
    max_files_per_subdir: int = -1,
    max_files_total: int = -1,
    include_dirs: bool = False,
) -> Generator[FileList, None, None]:
    """
    Simple wrapper around `os.walk`. Yields all files in each folder as a
    `FileList`. Filenames are relative to `parent_dir`, which is relative to
    `relative_to`. Handles sorting by name and skipping ignored files and
    directories based on the `ignore` filter.

    :param max_depth: Maximum depth to recurse into directories. -1 means no limit.
    :param max_files_per_subdir: Maximum number of files to yield per subdirectory.
    :param max_files_total: Maximum total number of files to yield.
    :param include_dirs: Whether to include directory entries in the output.
    """

    start_path = start_path.resolve()
    if not start_path.exists():
        raise FileNotFound(f"Start path not found: {fmt_loc(start_path)}")

    if relative_to:
        relative_to = relative_to.resolve()
        if not relative_to.exists():
            raise FileNotFound(f"Directory not found: {fmt_loc(relative_to)}")

    # Special case of a single file.
    if start_path.is_file():
        parent_dir = relpath(start_path.parent, relative_to) if relative_to else start_path.parent
        yield FileList(
            parent_dir,
            [start_path.name],
            None,
            files_ignored=0,
            dirs_ignored=0,
            files_skipped=0,
            dirs_skipped=0,
            num_files=1,
        )
        return

    files_so_far = 0
    for dirname, dirnames, filenames in os.walk(start_path):
        current_depth = len(Path(dirname).relative_to(start_path).parts)
        log.debug(
            "walk: depth %s: %s: %s dirs, %s files",
            current_depth,
            dirname,
            len(dirnames),
            len(filenames),
        )

        # Original counts.
        num_dirs = len(dirnames)
        num_files = len(filenames)

        # Filter out ignored directories.
        if ignore:
            # Careful: ignore("foo") is false even if "foo/" is ignored.
            dirnames[:] = [d for d in dirnames if not ignore(d, is_dir=True)]
            dirs_ignored = num_dirs - len(dirnames)
        else:
            dirs_ignored = 0

        # Keep untruncated dirnames for listing.
        dirnames_copy = dirnames.copy()

        # Truncate dirnames for recursion, handling max_depth.
        if max_depth >= 0 and current_depth >= max_depth:
            dirnames[:] = []

        # Sort directories and files.
        # TODO: Custom sort function so walk can prioritize by other criteria.
        dirnames.sort()
        dirnames_copy.sort()
        filenames.sort()

        # Filter out ignored files.
        if ignore:
            # Could also check `not ignore(os.path.join(dirname, f)` but that's kind of
            # aggressive if .* is in your ignore list.
            filenames = [f for f in filenames if not ignore(f)]
            files_ignored = num_files - len(filenames)
        else:
            files_ignored = 0

        # Now cap number of files.
        num_files_uncapped = num_files_capped = len(filenames)
        num_dirs_uncapped = num_dirs_capped = len(dirnames)

        # Apply max_files_per_subdir (but not at the top level, since that's confusing).
        at_top_level = dirname == str(start_path)
        if max_files_per_subdir > 0 and not at_top_level:
            filenames = filenames[:max_files_per_subdir]

        # Apply max_files limit
        if max_files_total > 0:
            files_remaining = max_files_total - files_so_far
            if files_remaining <= 0:
                # Stop traversal
                dirnames[:] = []
                num_dirs_capped = 0
                break
            if num_files_capped > files_remaining:
                filenames = filenames[:files_remaining]
                num_files_capped = len(filenames)

        files_so_far += num_files_capped

        parent_dir = relpath(abspath(dirname), relative_to) if relative_to else dirname

        should_include_dirs = include_dirs and current_depth <= max_depth

        yield FileList(
            parent_dir,
            filenames,
            dirnames_copy if should_include_dirs else None,
            files_ignored,
            dirs_ignored,
            files_skipped=num_files_uncapped - num_files_capped,
            dirs_skipped=num_dirs_uncapped - num_dirs_capped,
            num_files=num_files,
        )

        # Check if max_files limit is reached after adding files
        if max_files_total > 0 and files_so_far >= max_files_total:
            dirnames[:] = []
            break
