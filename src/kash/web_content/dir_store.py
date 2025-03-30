import logging
import os
from collections.abc import Callable
from os import path
from pathlib import Path
from typing import TypeAlias

from strif import clean_alphanum_hash, file_mtime_hash

from kash.utils.common.url import Url

log = logging.getLogger(__name__)


def aws_cli(*cmd):
    # Import dynamically to avoid hard dependency.
    from awscli.clidriver import create_clidriver  # pyright: ignore

    log.info("awscli: aws %s" % " ".join(cmd))
    # Run awscli in the same process
    exit_code = create_clidriver().main(cmd)

    # Deal with problems
    if exit_code > 0:
        raise RuntimeError(f"AWS CLI exited with code {exit_code}")


def string_hash(key: str) -> str:
    return clean_alphanum_hash(key, max_length=80)


HashFunc: TypeAlias = Callable[[str | Path], str]
"""
Hash to determine cache filename and identity.
"""


def default_hash_func(key: str | Path) -> str:
    if isinstance(key, Path):
        return file_mtime_hash(key)
    elif isinstance(key, str):
        return string_hash(key)
    else:
        raise ValueError(f"Invalid key type: {type(key)}")


class DirStore:
    """
    A simple file storage scheme: A directory of items, organized into folders, stored
    with names based on a consistent hash-based naming scheme.

    File naming and identity is determined by the `hash_func`. The default hash function
    supports naming files based on a string key or file name, with fast file identity
    based on `file_mtime_hash`.
    """

    # TODO: Would be useful to support optional additional root directories, with write always
    # being to the main root but cache lookups checking in sequence, allowing a hierarchy of caches.

    def __init__(self, root: Path, hash_func: HashFunc | None = None) -> None:
        self.root: Path = root
        self.hash_func: HashFunc = hash_func or default_hash_func
        os.makedirs(self.root, exist_ok=True)

    def path_for(
        self, key: str | Path, folder: str | None = None, suffix: str | None = None
    ) -> Path:
        """
        A unique file path with the given key. It's up to the client how to use it.
        """
        path_str = self.hash_func(key)

        if suffix:
            path_str += suffix
        path = Path(folder) / path_str if folder else Path(path_str)
        full_path = self.root / path

        return full_path

    def find(
        self, key: str | Path, folder: str | None = None, suffix: str | None = None
    ) -> Path | None:
        cache_path = self.path_for(key, folder, suffix)
        return cache_path if path.exists(cache_path) else None

    def find_all(
        self, keys: list[str | Path], folder: str | None = None, suffix: str | None = None
    ) -> dict[str | Path, Path | None]:
        """
        Look up all existing cached results for the set of keys. This should work fine but could
        be optimized for large batches.
        """
        return {key: self.find(key, folder=folder, suffix=suffix) for key in keys}

    def _restore(self, url: Url, folder: str = "") -> None:
        # We *don't* add '--delete' arg to delete remote files based on local status.
        aws_cli("s3", "sync", path.join(url, folder), self.root / folder)

    def _backup(self, url: Url, folder: str = "") -> None:
        # We *don't* add '--delete' arg to delete local files based on remote status.
        aws_cli("s3", "sync", self.root / folder, path.join(url, folder))

    # TODO: Consider other methods to purge or sync with --delete.
