import copy
import logging
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Generic, TypeVar

from cachetools import LRUCache
from strif import file_mtime_hash

log = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class CacheStats:
    hits: int = 0
    misses: int = 0
    updates: int = 0
    deletes: int = 0


class MtimeCache(Generic[T]):
    """
    A simple in-memory LRU cache that stores loaded values from files, with
    mtime-based expiration.
    """

    def __init__(self, max_size, name: str, log_freq: int = 500):
        self.cache: LRUCache[str, tuple[str, T]] = LRUCache(maxsize=max_size)
        self.lock = threading.RLock()
        self.stats = CacheStats()
        self.prev_stats = CacheStats()  # Initialize prev_stats with CacheStats
        self.name = name
        self.log_freq = log_freq

    def _cache_key(self, path: Path) -> str:
        return str(path.resolve())

    def read(self, path: Path) -> T | None:
        """
        Returns the cached item (actually a deep copy to be safe) if the item is present
        and the file hasn't changed; otherwise, returns None.
        """
        key = self._cache_key(path)
        mtime_hash = file_mtime_hash(path)
        with self.lock:
            self.log_stats()
            cache_entry = self.cache.get(key)
            if cache_entry:
                cached_mtime_hash, cached_value = cache_entry
                if cached_mtime_hash == mtime_hash:
                    self.stats.hits += 1
                    return copy.deepcopy(cached_value)
                else:
                    # Cache is outdated.
                    del self.cache[key]
            self.stats.misses += 1

        return None

    def update(self, path: Path, value: T) -> None:
        """
        Updates the cache with the new value for the given path.
        """
        key = self._cache_key(path)
        value = copy.deepcopy(value)
        mtime_hash = file_mtime_hash(path)
        with self.lock:
            self.log_stats()
            self.cache[key] = (mtime_hash, value)
            self.stats.updates += 1

    def delete(self, path: Path) -> None:
        """
        Removes the cached value for the given path.
        """
        key = self._cache_key(path)
        with self.lock:
            self.log_stats()
            if key in self.cache:
                del self.cache[key]
                self.stats.deletes += 1

    def log_stats(self) -> None:
        """
        Logs the cache statistics if any of the counters have changed by more than 100
        since the last time they were logged.
        """
        if self._stats_changed(self.log_freq):
            log.info(
                f"{self.name} file cache stats: hits: {self.stats.hits}, misses: {self.stats.misses}, "
                f"updates: {self.stats.updates}, deletes: {self.stats.deletes}"
            )
            self.prev_stats = copy.deepcopy(self.stats)

    def _stats_changed(self, threshold: int) -> bool:
        return (
            max(
                self.stats.hits - self.prev_stats.hits,
                self.stats.misses - self.prev_stats.misses,
                self.stats.updates - self.prev_stats.updates,
                self.stats.deletes - self.prev_stats.deletes,
            )
            > threshold
        )
