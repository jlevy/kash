import logging
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from strif import atomic_output_file, copyfile_atomic
from tqdm import tqdm

from kash.utils.common.url import Url

log = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (Compatible)"

DEFAULT_TIMEOUT = 30


def default_headers() -> dict[str, str]:
    return {"User-Agent": USER_AGENT}


def fetch_url(
    url: Url,
    timeout: int = DEFAULT_TIMEOUT,
    auth: Any | None = None,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    """
    Fetch a URL using httpx with logging and reasonable defaults.
    Raise httpx.HTTPError for non-2xx responses.
    """
    with httpx.Client(
        follow_redirects=True,
        timeout=timeout,
        auth=auth,
        headers=headers or default_headers(),
    ) as client:
        response = client.get(url)
        log.info("Fetched: %s (%s bytes): %s", response.status_code, len(response.content), url)
        response.raise_for_status()
        return response


def download_url(
    url: Url,
    target_filename: str | Path,
    session: httpx.Client | None = None,
    show_progress: bool = False,
    timeout: int = DEFAULT_TIMEOUT,
    auth: Any | None = None,
    headers: dict[str, str] | None = None,
) -> None:
    """
    Download given file, optionally with progress bar.
    Also handles file:// and s3:// URLs. Output file is created atomically.
    Raise httpx.HTTPError for non-2xx responses.
    """
    target_filename = str(target_filename)
    parsed_url = urlparse(url)
    if show_progress:
        log.info("%s", url)

    if parsed_url.scheme == "file" or parsed_url.scheme == "":
        copyfile_atomic(parsed_url.netloc + parsed_url.path, target_filename)
    elif parsed_url.scheme == "s3":
        import boto3  # pyright: ignore

        s3 = boto3.resource("s3")
        s3_path = parsed_url.path.lstrip("/")
        s3.Bucket(parsed_url.netloc).download_file(s3_path, target_filename)
    else:
        client = session or httpx.Client(follow_redirects=True, timeout=timeout)
        response: httpx.Response | None = None
        try:
            with client.stream(
                "GET",
                url,
                follow_redirects=True,
                timeout=timeout,
                auth=auth,
                headers=headers or default_headers(),
            ) as response:
                response.raise_for_status()
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
