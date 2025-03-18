from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SizeInfo:
    total_size: int
    file_count: int
    dir_count: int
    symlink_count: int
    other_count: int

    @property
    def total_count(self) -> int:
        return self.file_count + self.dir_count + self.symlink_count + self.other_count

    def is_empty(self) -> bool:
        return self.file_count == 0 and self.dir_count == 0 and self.other_count == 0


def get_dir_size(path: Path) -> SizeInfo:
    """
    Get tallies of all files, directories, and other items in the given directory.
    """

    total_size = 0
    file_count = 0
    dir_count = 0
    symlink_count = 0
    other_count = 0

    for file_path in path.rglob("*"):
        if file_path.is_file():
            file_count += 1
            total_size += file_path.stat().st_size
        elif file_path.is_dir():
            dir_count += 1
        elif file_path.is_symlink():
            symlink_count += 1
        else:
            other_count += 1

    return SizeInfo(total_size, file_count, dir_count, symlink_count, other_count)


def is_nonempty_dir(path: str | Path) -> bool:
    path = Path(path)
    return path.is_dir() and get_dir_size(path).file_count > 0
