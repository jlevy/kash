from __future__ import annotations

import logging
import ssl
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from functools import cache, cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from cachetools import TTLCache
from strif import atomic_output_file, copyfile_atomic

from kash.config.env_settings import KashEnv
from kash.utils.common.s3_utils import s3_download_file
from kash.utils.common.url import Url
from kash.utils.file_utils.file_formats import MimeType

log = logging.getLogger(__name__)


def _httpx_verify_context() -> ssl.SSLContext | bool:
    """
    Return an SSLContext that uses the system trust store via truststore, if available.
    Falls back to certifi bundle; otherwise True to use httpx defaults.
    """
    try:
        import truststore

        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except Exception:
        try:
            import certifi

            return ssl.create_default_context(cafile=certifi.where())
        except Exception:
            return True


def _stream_to_file(
    target_filename: str | Path,
    response_iterator: Iterable[bytes],
    total_size: int,
    show_progress: bool,
) -> None:
    with atomic_output_file(target_filename, make_parents=True) as temp_filename:
        with open(temp_filename, "wb") as f:
            if not show_progress:
                for chunk in response_iterator:
                    if chunk:
                        f.write(chunk)
            else:
                from tqdm import tqdm

                with tqdm(
                    total=total_size,
                    unit="B",
                    unit_scale=True,
                    desc=f"Downloading {Path(str(target_filename)).name}",
                ) as progress:
                    for chunk in response_iterator:
                        if chunk:
                            f.write(chunk)
                            progress.update(len(chunk))


def _httpx_fetch(
    url: Url,
    *,
    timeout: int,
    auth: Any | None,
    headers: dict[str, str] | None,
    mode: ClientMode,
    log_label: str,
):
    import httpx

    req_headers = _get_req_headers(mode, headers)
    parsed_url = urlparse(str(url))
    with httpx.Client(
        follow_redirects=True,
        timeout=timeout,
        auth=auth,
        headers=req_headers,
        verify=_httpx_verify_context(),
    ) as client:
        log.debug("fetch_url (%s): using headers: %s", log_label, client.headers)
        if mode is ClientMode.BROWSER_HEADERS:
            _prime_host(parsed_url.netloc, client, timeout)
        response = client.get(url)
        log.info(
            "Fetched (%s): %s (%s bytes): %s",
            log_label,
            response.status_code,
            len(response.content),
            url,
        )
        response.raise_for_status()
        return response


def _httpx_download(
    url: Url,
    target_filename: str | Path,
    *,
    show_progress: bool,
    timeout: int,
    auth: Any | None,
    headers: dict[str, str] | None,
    mode: ClientMode,
    log_label: str,
) -> dict[str, str]:
    import httpx

    req_headers = _get_req_headers(mode, headers)
    parsed_url = urlparse(str(url))
    with httpx.Client(
        follow_redirects=True,
        timeout=timeout,
        headers=req_headers,
        verify=_httpx_verify_context(),
    ) as client:
        if mode is ClientMode.BROWSER_HEADERS:
            _prime_host(parsed_url.netloc, client, timeout)
        log.debug("download_url (%s): using headers: %s", log_label, client.headers)
        with client.stream("GET", url, auth=auth, follow_redirects=True) as response:
            response.raise_for_status()
            response_headers = dict(response.headers)
            total = int(response.headers.get("content-length", "0"))
            _stream_to_file(target_filename, response.iter_bytes(), total, show_progress)
            return response_headers


def _is_tls_cert_error(exc: Exception) -> bool:
    """
    Heuristic detection of TLS/certificate verification errors coming from curl_cffi/libcurl.
    """
    s = str(exc).lower()
    if "curl: (60)" in s:
        return True
    if "certificate verify failed" in s:
        return True
    if "ssl" in s and ("certificate" in s or "cert" in s or "handshake" in s):
        return True
    return False


if TYPE_CHECKING:
    from curl_cffi.requests import Response as CurlCffiResponse
    from curl_cffi.requests import Session as CurlCffiSession
    from httpx import Client as HttpxClient
    from httpx import Response as HttpxResponse


DEFAULT_TIMEOUT = 30
CURL_CFFI_IMPERSONATE_VERSION = "chrome120"

# Header helpers
_DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_3) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)
_SIMPLE_HEADERS = {"User-Agent": KashEnv.KASH_USER_AGENT.read_str(default=_DEFAULT_UA)}


class ClientMode(Enum):
    """
    Defines the web client and settings.
    """

    SIMPLE = "SIMPLE"
    """httpx with minimal headers"""

    BROWSER_HEADERS = "BROWSER_HEADERS"
    """httpx with extensive, manually-set headers"""

    CURL_CFFI = "CURL_CFFI"
    """curl_cffi for full browser impersonation (incl. TLS)"""

    AUTO = "AUTO"
    """Automatically pick CURL_CFFI if available, otherwise BROWSER_HEADERS"""


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
def _have_curl_cffi() -> bool:
    """
    Check if curl_cffi is available.
    Warns once if curl_cffi is not installed.
    """
    try:
        import curl_cffi.requests  # noqa: F401

        return True
    except ImportError:
        log.warning("web_fetch: curl_cffi package not found; install for browser impersonation")
        return False


@cache
def _get_auto_mode() -> ClientMode:
    """
    Automatically select the best available client mode.
    Logs the decision once due to caching.
    """
    if _have_curl_cffi():
        log.info("web_fetch: AUTO mode selected CURL_CFFI (full browser impersonation)")
        return ClientMode.CURL_CFFI
    else:
        log.info("web_fetch: AUTO mode selected BROWSER_HEADERS (httpx with browser headers)")
        return ClientMode.BROWSER_HEADERS


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


def _prime_host(host: str, client: HttpxClient | CurlCffiSession, timeout: int, **kwargs) -> bool:
    """
    Prime cookies for a host using the provided client and extra arguments.
    """
    if host in _primed_hosts:
        log.debug("Cookie priming for %s skipped (cached)", host)
        return True

    try:
        root = f"https://{host}/"
        # Pass client-specific kwargs like `impersonate`
        client.get(root, timeout=timeout, **kwargs)
        log.debug("Cookie priming completed for %s", host)
    except Exception as exc:
        log.debug("Cookie priming for %s failed (%s); continuing", host, exc)

    # Mark as primed (both success and failure to avoid immediate retries)
    _primed_hosts[host] = True
    return True


def _get_req_headers(
    mode: ClientMode, user_headers: dict[str, str] | None = None
) -> dict[str, str]:
    """
    Build headers based on the selected ClientMode.
    For CURL_CFFI, curl_cffi handles headers automatically.
    """
    if mode is ClientMode.AUTO:
        mode = _get_auto_mode()

    base_headers = {}
    if mode is ClientMode.SIMPLE:
        base_headers = _SIMPLE_HEADERS
    elif mode is ClientMode.BROWSER_HEADERS:
        base_headers = _browser_like_headers()
    elif mode is ClientMode.CURL_CFFI:
        # curl_cffi handles the important headers (UA, Accept-*, etc.)
        # We only need to add user-provided ones.
        return user_headers or {}

    if user_headers:
        return {**base_headers, **user_headers}

    return base_headers


def fetch_url(
    url: Url,
    *,
    timeout: int = DEFAULT_TIMEOUT,
    auth: Any | None = None,
    headers: dict[str, str] | None = None,
    mode: ClientMode = ClientMode.AUTO,
) -> HttpxResponse | CurlCffiResponse:
    """
    Fetch a URL, dispatching to httpx or curl_cffi based on the mode.
    """
    if mode is ClientMode.AUTO:
        mode = _get_auto_mode()

    req_headers = _get_req_headers(mode, headers)
    parsed_url = urlparse(str(url))

    # Handle curl_cffi mode
    if mode is ClientMode.CURL_CFFI:
        if not _have_curl_cffi():
            raise ValueError("Could not find curl_cffi, which is needed for CURL_CFFI mode")

        from curl_cffi.requests import Session

        exc: Exception | None = None
        try:
            with Session() as client:
                # Set headers on the session - they will be sent with all requests
                client.headers.update(req_headers)
                _prime_host(
                    parsed_url.netloc, client, timeout, impersonate=CURL_CFFI_IMPERSONATE_VERSION
                )
                log.debug("fetch_url (curl_cffi): using session headers: %s", client.headers)
                response = client.get(
                    url,
                    impersonate=CURL_CFFI_IMPERSONATE_VERSION,
                    timeout=timeout,
                    auth=auth,
                    allow_redirects=True,
                )
                log.info(
                    "Fetched (curl_cffi): %s (%s bytes): %s",
                    response.status_code,
                    len(response.content),
                    url,
                )
                response.raise_for_status()
                return response
        except Exception as e:
            exc = e

        if exc and _is_tls_cert_error(exc):
            log.warning(
                "TLS/SSL verification failed with curl_cffi for %s: %s; falling back to httpx",
                url,
                exc,
            )
            # Fallback to httpx with browser-like headers (uses system trust if available)
            return _httpx_fetch(
                url,
                timeout=timeout,
                auth=auth,
                headers=headers,
                mode=ClientMode.BROWSER_HEADERS,
                log_label="httpx fallback",
            )

        if exc:
            raise exc

    # Handle httpx modes
    else:
        return _httpx_fetch(
            url, timeout=timeout, auth=auth, headers=headers, mode=mode, log_label="httpx"
        )


@dataclass(frozen=True)
class HttpHeaders:
    headers: dict[str, str]

    @cached_property
    def mime_type(self) -> MimeType | None:
        for key, value in self.headers.items():
            if key.lower() == "content-type":
                return MimeType(value)
        return None


def download_url(
    url: Url,
    target_filename: str | Path,
    *,
    show_progress: bool = False,
    timeout: int = DEFAULT_TIMEOUT,
    auth: Any | None = None,
    headers: dict[str, str] | None = None,
    mode: ClientMode = ClientMode.AUTO,
) -> HttpHeaders | None:
    """
    Download given file, optionally with progress bar, streaming to a target file.
    Also handles file:// and s3:// URLs. Output file is created atomically.
    Raise httpx.HTTPError for non-2xx responses.
    Returns response headers for HTTP/HTTPS requests, None for other URL types.
    """
    if mode is ClientMode.AUTO:
        mode = _get_auto_mode()

    target_filename = str(target_filename)
    parsed_url = urlparse(url)
    if show_progress:
        log.info("%s", url)

    if parsed_url.scheme == "file" or parsed_url.scheme == "":
        copyfile_atomic(parsed_url.netloc + parsed_url.path, target_filename, make_parents=True)
        return None
    elif parsed_url.scheme == "s3":
        with atomic_output_file(target_filename, make_parents=True) as temp_filename:
            s3_download_file(url, temp_filename)
        return None

    req_headers = _get_req_headers(mode, headers)
    response_headers = None

    # Handle curl_cffi mode
    if mode is ClientMode.CURL_CFFI:
        if not _have_curl_cffi():
            raise ValueError("Could not find curl_cffi, which is needed for CURL_CFFI mode")

        from curl_cffi.requests import Session

        exc: Exception | None = None
        try:
            with Session() as client:
                # Set headers on the session; they will be sent with all requests
                client.headers.update(req_headers)
                _prime_host(
                    parsed_url.netloc, client, timeout, impersonate=CURL_CFFI_IMPERSONATE_VERSION
                )
                log.debug("download_url (curl_cffi): using session headers: %s", client.headers)
                response = client.get(
                    url,
                    impersonate=CURL_CFFI_IMPERSONATE_VERSION,
                    timeout=timeout,
                    auth=auth,
                    allow_redirects=True,
                    stream=True,
                )
                response.raise_for_status()
                response_headers = dict(response.headers)
                total = int(response.headers.get("content-length", "0"))

                # Use iter_content for streaming; this is the standard method for curl_cffi
                chunk_iterator = response.iter_content(chunk_size=8192)
                _stream_to_file(target_filename, chunk_iterator, total, show_progress)
        except Exception as e:
            exc = e

        if exc and _is_tls_cert_error(exc):
            log.warning(
                "TLS/SSL verification failed with curl_cffi for %s: %s; falling back to httpx",
                url,
                exc,
            )
            # Fallback to httpx streaming with browser-like headers (system trust store if available)
            response_headers = _httpx_download(
                url,
                target_filename,
                show_progress=show_progress,
                timeout=timeout,
                auth=auth,
                headers=headers,
                mode=ClientMode.BROWSER_HEADERS,
                log_label="httpx fallback",
            )
        elif exc:
            raise exc

    # Handle httpx modes
    else:
        response_headers = _httpx_download(
            url,
            target_filename,
            show_progress=show_progress,
            timeout=timeout,
            auth=auth,
            headers=headers,
            mode=mode,
            log_label="httpx",
        )

    # Filter out None values from headers for HttpHeaders type compatibility
    if response_headers:
        clean_headers = {k: v for k, v in response_headers.items() if v is not None}
        return HttpHeaders(clean_headers)
    return None


def main() -> None:
    """
    Simple CLI test harness for fetch and download.

    Usage examples:
      uv run python -m kash.web_content.web_fetch
      uv run python -m kash.web_content.web_fetch https://www.example.com
    """
    import sys
    import traceback

    # Try to use the system trust store for TLS like command-line curl
    try:
        import truststore  # type: ignore

        truststore.inject_into_ssl()
        log.warning("truststore initialized for test harness: using system TLS trust store")
    except Exception as exc:
        log.info("truststore not available for test harness; using default TLS trust (%s)", exc)

    urls = [
        "https://www.example.com",
        "https://www.businessdefense.gov/ibr/mceip/dpai/dpat3/index.html",
    ]

    args = [a for a in sys.argv[1:] if a and a.strip()]
    if args:
        urls = args

    for u in urls:
        try:
            log.warning("Testing fetch_url: %s", u)
            r = fetch_url(Url(u))
            log.warning("fetch_url OK: %s -> %s bytes", u, len(r.content))
        except Exception as exc:
            log.exception("fetch_url FAILED for %s: %s", u, exc)
            traceback.print_exc()


if __name__ == "__main__":
    main()
