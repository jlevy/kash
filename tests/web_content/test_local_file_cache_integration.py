"""
Integration tests for LocalFileCache with real filesystem operations.
"""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from kash.web_content.local_file_cache import (
    CacheResult,
    LocalFileCache,
    Loadable,
    read_mtime,
)

# Expiration constants are class attributes on LocalFileCache.
ALWAYS = LocalFileCache.ALWAYS
NEVER = LocalFileCache.NEVER


class TestLocalFileCacheBasics:
    """Basic cache lifecycle tests using tmp_path."""

    def test_cache_loadable(self, tmp_path):
        """Caching a Loadable should write it and return was_cached=False first time."""
        cache = LocalFileCache(root=tmp_path, default_expiration_sec=NEVER)

        def save_fn(path: Path):
            path.write_text("generated content")

        loadable = Loadable(key="test_item.txt", save=save_fn)
        result = cache.cache(loadable)

        assert not result.was_cached
        assert result.content.path.exists()
        assert result.content.path.read_text() == "generated content"

    def test_cache_loadable_second_time(self, tmp_path):
        """Second cache call should return was_cached=True."""
        cache = LocalFileCache(root=tmp_path, default_expiration_sec=NEVER)

        def save_fn(path: Path):
            path.write_text("generated content")

        loadable = Loadable(key="test_item.txt", save=save_fn)

        # First call: not cached.
        result1 = cache.cache(loadable)
        assert not result1.was_cached

        # Second call: cached.
        result2 = cache.cache(loadable)
        assert result2.was_cached
        assert result2.content.path == result1.content.path

    def test_cache_expiration(self, tmp_path):
        """Expired items should be re-loaded."""
        cache = LocalFileCache(root=tmp_path, default_expiration_sec=0.01)  # 10ms

        call_count = 0

        def save_fn(path: Path):
            nonlocal call_count
            call_count += 1
            path.write_text(f"content v{call_count}")

        loadable = Loadable(key="expiring.txt", save=save_fn)

        result1 = cache.cache(loadable)
        assert not result1.was_cached
        assert call_count == 1

        # Wait for expiration.
        time.sleep(0.05)

        result2 = cache.cache(loadable)
        assert not result2.was_cached
        assert call_count == 2

    def test_cache_never_expires(self, tmp_path):
        """Items with NEVER expiration should always be cached."""
        cache = LocalFileCache(root=tmp_path, default_expiration_sec=NEVER)

        def save_fn(path: Path):
            path.write_text("permanent")

        loadable = Loadable(key="permanent.txt", save=save_fn)
        cache.cache(loadable)
        result = cache.cache(loadable)
        assert result.was_cached

    def test_is_cached(self, tmp_path):
        cache = LocalFileCache(root=tmp_path, default_expiration_sec=NEVER)

        loadable = Loadable(key="check.txt", save=lambda p: p.write_text("hi"))

        assert not cache.is_cached(loadable)
        cache.cache(loadable)
        assert cache.is_cached(loadable)


class TestLocalFileCachePaths:
    """Test cache with Path inputs."""

    def test_cache_local_file(self, tmp_path):
        """Caching a local Path should copy it to the cache."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        cache = LocalFileCache(root=cache_dir, default_expiration_sec=NEVER)

        source = tmp_path / "source.txt"
        source.write_text("local file data")

        result = cache.cache(source)
        assert not result.was_cached
        assert result.content.path.exists()
        assert result.content.path.read_text() == "local file data"
        # Cached file should be in cache dir, not the original.
        assert str(result.content.path).startswith(str(cache_dir))


class TestReadMtime:
    """Test mtime reading helper."""

    def test_read_mtime(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("content")
        mtime = read_mtime(f)
        assert mtime > 0

    def test_read_mtime_missing_file(self, tmp_path):
        f = tmp_path / "nonexistent.txt"
        mtime = read_mtime(f)
        assert mtime == 0.0
