from datetime import UTC, datetime
from enum import Enum
from pathlib import Path

import humanfriendly
import pandas as pd
from funlog import log_calls
from prettyfmt import fmt_path
from pydantic.dataclasses import dataclass

from kash.config.logger import get_logger
from kash.utils.errors import FileNotFound, InvalidInput
from kash.utils.file_utils.file_walk import IgnoreFilter, walk_by_dir

log = get_logger(__name__)


class SortOption(str, Enum):
    filename = "filename"
    size = "size"
    accessed = "accessed"
    created = "created"
    modified = "modified"


class GroupByOption(str, Enum):
    flat = "flat"
    parent = "parent"
    suffix = "suffix"


class FileType(str, Enum):
    file = "file"
    dir = "dir"


@dataclass(frozen=True)
class FileInfo:
    """
    Information about a file for a file listing. Note we use primitive
    string/datetime types for convenient sorting/grouping listings with pandas.
    """

    path: str
    relative_path: str
    filename: str
    suffix: str
    parent: str
    size: int
    accessed: datetime
    created: datetime
    modified: datetime
    type: FileType


# FIXME: Expand FileInfo and add * for executable and @ (with target) for symlinks.
def type_suffix(file_info: FileInfo) -> str:
    return "/" if file_info.type == FileType.dir else ""


def get_file_info(
    file_path: Path, base_path: Path, resolve_parent: bool = False, follow_symlinks: bool = False
) -> FileInfo:
    """
    Stat file and get info about it. Uses `base_path` to calculate `relative_path`
    and `parent` (unless `resolve_parent` is true, in which case the parent will
    be resolved to an absolute path).
    """
    stat = file_path.stat(follow_symlinks=follow_symlinks)
    # Special case that if base path is the root, all paths are absolute.
    if base_path.resolve() == Path("/"):
        relative_path = file_path.resolve()
        parent = Path("/")
    else:
        relative_path = file_path.relative_to(base_path)
        parent = (
            file_path.parent.resolve()
            if resolve_parent
            else file_path.parent.relative_to(base_path)
        )

    return FileInfo(
        path=str(file_path.resolve()),
        relative_path=str(relative_path),
        filename=file_path.name,
        suffix=file_path.suffix,
        parent=str(parent),
        size=stat.st_size,
        accessed=datetime.fromtimestamp(stat.st_atime, tz=UTC),
        created=datetime.fromtimestamp(stat.st_ctime, tz=UTC),
        modified=datetime.fromtimestamp(stat.st_mtime, tz=UTC),
        type=FileType.dir if file_path.is_dir() else FileType.file,
    )


def parse_since(since: str) -> float:
    try:
        since_seconds = humanfriendly.parse_timespan(since)
        return since_seconds
    except humanfriendly.InvalidTimespan:
        raise InvalidInput(
            f"Invalid 'since' format '{since}'. "
            "Use formats like '5m' (5 minutes), '1d' (1 day), or '2w' (2 weeks)."
        )


@dataclass
class FileListing:
    """
    Results of walking a directory and collecting file information.
    """

    files: list[FileInfo]
    start_paths: list[Path]
    files_total: int
    files_matching: int
    files_ignored: int  # Due to ignore rules.
    dirs_ignored: int  # Due to ignore rules.
    files_skipped: int  # Due to max caps.
    dirs_skipped: int  # Due to max caps.
    size_total: int
    size_matching: int
    since_timestamp: float

    def as_dataframe(self) -> pd.DataFrame:
        df = pd.DataFrame([file.__dict__ for file in self.files])
        return df

    @property
    def total_ignored(self) -> int:
        return self.files_ignored + self.dirs_ignored

    @property
    def total_skipped(self) -> int:
        return self.files_skipped + self.dirs_skipped


@log_calls(level="debug")
def collect_files(
    start_paths: list[Path],
    max_depth: int = -1,
    max_files_per_subdir: int = -1,
    max_files_total: int = -1,
    ignore: IgnoreFilter | None = None,
    since_seconds: float = 0.0,
    base_path: Path | None = None,
    resolve_parent: bool = False,
    include_dirs: bool = False,
) -> FileListing:
    files_info: list[FileInfo] = []

    for path in start_paths:
        if not path.exists():
            raise FileNotFound(f"Path not found: {fmt_path(path)}")

    since_timestamp = datetime.now(UTC).timestamp() - since_seconds if since_seconds else 0.0
    if since_timestamp:
        log.info(
            "Collecting files modified in last %s seconds (since %s).",
            since_seconds,
            datetime.fromtimestamp(since_timestamp),
        )

    files_total = 0
    size_total = 0
    size_matching = 0

    dirs_ignored = 0
    files_ignored = 0
    dirs_skipped = 0
    files_skipped = 0

    if not base_path:
        base_path = Path(".")

    for path in start_paths:
        log.debug("Walking folder: %s", fmt_path(path))

        try:
            for flist in walk_by_dir(
                path,
                relative_to=base_path,
                ignore=ignore,
                max_depth=max_depth,
                max_files_per_subdir=max_files_per_subdir,
                max_files_total=max_files_total,
                include_dirs=include_dirs,
            ):
                log.debug("Walking folder: %s: %s", fmt_path(flist.parent_dir), flist.filenames)

                files_ignored += flist.files_ignored
                dirs_ignored += flist.dirs_ignored
                files_skipped += flist.files_skipped
                dirs_skipped += flist.dirs_skipped

                dir_path = base_path / flist.parent_dir

                if flist.dirnames:
                    for dirname in flist.dirnames:
                        info = get_file_info(
                            dir_path / dirname, base_path, resolve_parent=resolve_parent
                        )

                        if not since_timestamp or info.modified.timestamp() > since_timestamp:
                            files_info.append(info)

                for filename in flist.filenames:
                    info = get_file_info(
                        dir_path / filename, base_path, resolve_parent=resolve_parent
                    )

                    if not since_timestamp or info.modified.timestamp() > since_timestamp:
                        files_info.append(info)
                        size_matching += info.size

                    files_total += 1
                    size_total += info.size

        except FileNotFound as e:
            log.warning("File unexpectedly missing: %s", e)
            continue

    return FileListing(
        files=files_info,
        start_paths=start_paths,
        files_total=files_total,
        files_matching=len(files_info),
        files_ignored=files_ignored,
        dirs_ignored=dirs_ignored,
        files_skipped=files_skipped,
        dirs_skipped=dirs_skipped,
        size_total=size_total,
        size_matching=size_matching,
        since_timestamp=since_timestamp,
    )
