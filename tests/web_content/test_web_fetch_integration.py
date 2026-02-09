"""
Integration tests for web_fetch module.

Tests file:// URL handling (no mocking needed) and HttpHeaders parsing.
HTTP tests are skipped since httpx is imported lazily inside functions,
making it difficult to mock without modifying the production code.
"""

from __future__ import annotations

from kash.utils.common.url import Url
from kash.web_content.web_fetch import HttpHeaders, download_url


class TestDownloadFileUrl:
    """Tests for download_url with file:// URLs (no network needed)."""

    def test_download_file_url(self, tmp_path):
        """download_url should copy file:// URLs to target."""
        source = tmp_path / "source.txt"
        source.write_text("local file content")
        target = tmp_path / "target.txt"

        result = download_url(Url(f"file://{source}"), str(target))

        assert result is None  # file:// returns None (no HTTP headers)
        assert target.read_text() == "local file content"

    def test_download_file_url_binary(self, tmp_path):
        """download_url should handle binary file:// URLs."""
        source = tmp_path / "image.bin"
        source.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        target = tmp_path / "output.bin"

        download_url(Url(f"file://{source}"), str(target))

        assert target.read_bytes() == source.read_bytes()

    def test_download_file_url_overwrites(self, tmp_path):
        """download_url should overwrite existing target files."""
        source = tmp_path / "source.txt"
        source.write_text("new content")
        target = tmp_path / "target.txt"
        target.write_text("old content")

        download_url(Url(f"file://{source}"), str(target))

        assert target.read_text() == "new content"


class TestHttpHeaders:
    """Tests for HttpHeaders dataclass."""

    def test_mime_type_parsing(self):
        headers = HttpHeaders(headers={"content-type": "text/html; charset=utf-8"})
        assert headers.mime_type is not None
        assert "text/html" in str(headers.mime_type)

    def test_mime_type_missing(self):
        headers = HttpHeaders(headers={})
        assert headers.mime_type is None

    def test_mime_type_simple(self):
        headers = HttpHeaders(headers={"content-type": "application/json"})
        assert headers.mime_type == "application/json"

    def test_mime_type_with_boundary(self):
        headers = HttpHeaders(headers={"content-type": "multipart/form-data; boundary=abc"})
        assert headers.mime_type is not None
        assert "multipart/form-data" in str(headers.mime_type)

    def test_headers_are_frozen(self):
        headers = HttpHeaders(headers={"x-custom": "value"})
        assert headers.headers["x-custom"] == "value"
