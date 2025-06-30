from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import cache, cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from cachetools import TTLCache
from strif import atomic_output_file, copyfile_atomic

from kash.config.env_settings import KashEnv
from kash.utils.common.url import Url
from kash.utils.file_utils.file_formats import MimeType

if TYPE_CHECKING:
    from httpx import Client, Response

log = logging.getLogger(__name__)


DEFAULT_TIMEOUT = 30

# Header helpers
_DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_3) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)
_SIMPLE_HEADERS = {"User-Agent": KashEnv.KASH_USER_AGENT.read_str(default=_DEFAULT_UA)}


@cache
def _have_brotli() -> bool:
    """
    Check if brotli compression is available.
    Warns once if brotli is not installed.
    """
    try:
        import brotli  # noqa: F401

        return True
    except ImportError:
        log.warning("web_fetch: brotli package not found; install for better download performance")
        return False


@cache
def _browser_like_headers() -> dict[str, str]:
    """
    Full header set that looks like a 2025-era Chrome GET.
    """
    ua = KashEnv.KASH_USER_AGENT.read_str(default=_DEFAULT_UA)

    # Build Accept-Encoding based on available compression support
    encodings = ["gzip", "deflate"]
    if _have_brotli():
        encodings.append("br")
    accept_encoding = ", ".join(encodings)

    return {
        "User-Agent": ua,
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": accept_encoding,
        "Referer": "https://www.google.com/",
        "DNT": "1",
        "Upgrade-Insecure-Requests": "1",
    }


# Cookie priming cache - tracks which hosts have been primed
_primed_hosts = TTLCache(maxsize=10000, ttl=3600)


def _prime_cookies_for_host(host: str, client: Client, timeout: int) -> bool:
    """
    Prime cookies for a host by making a request to the site root.
    Uses TTL caching to avoid repeated priming of the same host.
    Returns True if priming was attempted or skipped due to cache.
    """
    if host in _primed_hosts:
        log.debug("Cookie priming for %s skipped (cached)", host)
        return True

    try:
        parsed_netloc = urlparse(f"https://{host}")
        root = f"{parsed_netloc.scheme}://{parsed_netloc.netloc}/"
        client.get(root, timeout=timeout)
        log.debug("Cookie priming completed for %s", host)
    except Exception as exc:
        log.debug("Cookie priming for %s failed (%s); continuing", host, exc)

    # Mark as primed (both success and failure to avoid immediate retries)
    _primed_hosts[host] = True
    return True


def _get_req_headers(
    enable_browser_headers: bool, user_headers: dict[str, str] | None = None
) -> dict[str, str]:
    """
    Build headers by merging browser/simple headers with user-provided headers.
    User headers take precedence over base headers.
    """
    base_headers = _browser_like_headers() if enable_browser_headers else _SIMPLE_HEADERS
    if user_headers:
        # Merge with user headers taking precedence
        merged = base_headers.copy()
        merged.update(user_headers)
        return merged
    return base_headers


def fetch_url(
    url: Url,
    *,
    timeout: int = DEFAULT_TIMEOUT,
    auth: Any | None = None,
    headers: dict[str, str] | None = None,
    enable_browser_headers: bool = True,
) -> Response:
    """
    Fetch a URL using httpx with logging and reasonable defaults.
    Raises httpx.HTTPError for non-2xx responses.

    When `enable_browser_headers` is True (default), a realistic browser
    fingerprint is used and the site root is visited first to collect any
    cookies (WAF friendliness). User-provided headers are merged on top of
    browser headers with user headers taking precedence.
    """
    import httpx

    req_headers = _get_req_headers(enable_browser_headers, headers)

    with httpx.Client(
        follow_redirects=True,
        timeout=timeout,
        auth=auth,
        headers=req_headers,
    ) as client:
        log.debug("fetch_url: using headers: %s", client.headers)

        # Cookie priming, only when browser headers enabled
        if enable_browser_headers:
            parsed = urlparse(str(url))
            _prime_cookies_for_host(parsed.netloc, client, timeout)

        response = client.get(url)
        log.info("Fetched: %s (%s bytes): %s", response.status_code, len(response.content), url)
        response.raise_for_status()
        return response


@dataclass(frozen=True)
class HttpHeaders:
    """
    HTTP response headers.
    """

    headers: dict[str, str]

    @cached_property
    def mime_type(self) -> MimeType | None:
        """Get content type header, if available."""
        for key, value in self.headers.items():
            if key.lower() == "content-type":
                return MimeType(value)
        return None


def download_url(
    url: Url,
    target_filename: str | Path,
    *,
    session: Client | None = None,
    show_progress: bool = False,
    timeout: int = DEFAULT_TIMEOUT,
    auth: Any | None = None,
    headers: dict[str, str] | None = None,
    enable_browser_headers: bool = True,
) -> HttpHeaders | None:
    """
    Download given file, optionally with progress bar, streaming to a target file.
    Also handles file:// and s3:// URLs. Output file is created atomically.
    Raise httpx.HTTPError for non-2xx responses.
    Returns response headers for HTTP/HTTPS requests, None for other URL types.
    """
    import httpx
    from tqdm import tqdm

    target_filename = str(target_filename)
    parsed_url = urlparse(url)
    if show_progress:
        log.info("%s", url)

    if parsed_url.scheme == "file" or parsed_url.scheme == "":
        copyfile_atomic(parsed_url.netloc + parsed_url.path, target_filename, make_parents=True)
        return None
    elif parsed_url.scheme == "s3":
        import boto3  # pyright: ignore

        s3 = boto3.resource("s3")
        s3_path = parsed_url.path.lstrip("/")
        s3.Bucket(parsed_url.netloc).download_file(s3_path, target_filename)
        return None

    else:
        client = session or httpx.Client(follow_redirects=True, timeout=timeout)
        response: httpx.Response | None = None
        req_headers = _get_req_headers(enable_browser_headers, headers)

        try:
            log.debug("download_url: using headers: %s", req_headers)
            if enable_browser_headers:
                # Cookie priming using cached approach
                _prime_cookies_for_host(parsed_url.netloc, client, timeout)

            with client.stream(
                "GET",
                url,
                follow_redirects=True,
                timeout=timeout,
                auth=auth,
                headers=req_headers,
            ) as response:
                response.raise_for_status()
                response_headers = dict(response.headers)
                total_size = int(response.headers.get("content-length", "0"))

                with atomic_output_file(target_filename, make_parents=True) as temp_filename:
                    with open(temp_filename, "wb") as f:
                        if not show_progress:
                            for chunk in response.iter_bytes():
                                f.write(chunk)
                        else:
                            with tqdm(total=total_size, unit="B", unit_scale=True) as progress:
                                for chunk in response.iter_bytes():
                                    f.write(chunk)
                                    progress.update(len(chunk))
        finally:
            if not session:  # Only close if we created the client
                client.close()
            if response:
                response.raise_for_status()  # In case of errors during streaming

        return HttpHeaders(response_headers) if response_headers else None


## Tests


# A reminder to install brotli.
def test_have_brotli():
    assert _have_brotli()
