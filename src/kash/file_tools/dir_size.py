from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SizeInfo:
    total_size: int
    file_count: int


def get_dir_size(path: Path) -> SizeInfo:
    """
    Get the total size and file count of a directory.
    """

    total_size = 0
    file_count = 0

    for file_path in path.rglob("*"):
        if file_path.is_file():
            file_count += 1
            total_size += file_path.stat().st_size

    return SizeInfo(total_size, file_count)


def is_nonempty_dir(path: Path) -> bool:
    return path.is_dir() and get_dir_size(path).file_count > 0
