from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from strif import atomic_output_file, copyfile_atomic

from kash.config.env_settings import KashEnv
from kash.utils.common.url import Url
from kash.utils.file_utils.file_formats import MimeType

if TYPE_CHECKING:
    from httpx import Client, Response

log = logging.getLogger(__name__)


DEFAULT_TIMEOUT = 30


DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:126.0) Gecko/20100101 Firefox/126.0"
)


def default_headers() -> dict[str, str]:
    return {"User-Agent": KashEnv.KASH_USER_AGENT.read_str(default=DEFAULT_USER_AGENT)}


def fetch_url(
    url: Url,
    timeout: int = DEFAULT_TIMEOUT,
    auth: Any | None = None,
    headers: dict[str, str] | None = None,
) -> Response:
    """
    Fetch a URL using httpx with logging and reasonable defaults.
    Raise httpx.HTTPError for non-2xx responses.
    """
    import httpx

    with httpx.Client(
        follow_redirects=True,
        timeout=timeout,
        auth=auth,
        headers=headers or default_headers(),
    ) as client:
        log.debug("fetch_url: using headers: %s", client.headers)
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
    session: Client | None = None,
    show_progress: bool = False,
    timeout: int = DEFAULT_TIMEOUT,
    auth: Any | None = None,
    headers: dict[str, str] | None = None,
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
        response_headers: dict[str, str] | None = None
        try:
            headers = headers or default_headers()
            log.debug("download_url: using headers: %s", headers)
            with client.stream(
                "GET",
                url,
                follow_redirects=True,
                timeout=timeout,
                auth=auth,
                headers=headers,
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
