from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import requests
from pyrate_limiter import Duration, Limiter, Rate
from pyrate_limiter.buckets import InMemoryBucket
from typing_extensions import override

from kash.config.logger import get_logger
from kash.web_content.file_cache_utils import cache_file
from kash.web_content.local_file_cache import Loadable

log = get_logger(__name__)


class CachingSession(requests.Session):
    """
    A `requests.Session` that adds local file caching and optional rate limiting (if
    `limit` and `limit_interval_secs` are provided). A bit of a hack but enables
    hot patching libraries that use `requests` without other code changes.
    """

    def __init__(
        self,
        *,
        limit: int | None = None,
        limit_interval_secs: int | None = None,
        max_wait_secs: int = 60 * 5,
    ):
        super().__init__()
        self._limiter: Limiter | None = None
        self._max_wait_ms: int = max_wait_secs * 1000
        if limit and limit_interval_secs:
            rate = Rate(limit, Duration.SECOND * limit_interval_secs)
            bucket = InMemoryBucket([rate])
            self._limiter = Limiter(bucket)
            log.info(
                "CachingSession: rate limiting requests with limit=%d, interval=%d, max_wait=%d",
                limit,
                limit_interval_secs,
                max_wait_secs,
            )

    @override
    def get(self, url: str | bytes, **kwargs: Any) -> Any:
        params = kwargs.get("params")
        # We need a unique key for the cache, so we use the URL and params.
        url_str = url.decode() if isinstance(url, bytes) else str(url)
        query_string = urlencode(params or {})
        url_key = f"{url_str}?{query_string}" if query_string else url_str

        def save(path: Path):
            if self._limiter:
                # Use blocking mode with timeout (in ms) for rate limiting.
                acquired = self._limiter.try_acquire(
                    "caching_session_get", blocking=True, timeout=self._max_wait_ms
                )
                if not acquired:
                    # Generally shouldn't happen.
                    raise RuntimeError("Rate limiter failed to acquire after maximum delay")

            response = super(CachingSession, self).get(url, **kwargs)
            response.raise_for_status()
            content = response.content
            with open(path, "wb") as f:
                f.write(content)

        cache_result = cache_file(Loadable(url_key, save))

        if not cache_result.was_cached:
            log.debug("Cache miss, fetched: %s", url_key)
        else:
            log.debug("Cache hit: %s", url_key)

        # A simple hack to make sure response.json() works (e.g. when using wikipediaapi needs).
        # TODO: Wrap more carefully to ensure other methods work.
        response = requests.Response()
        response.status_code = 200
        response.encoding = "utf-8"
        response._content = cache_result.content.path.read_bytes()
        response.url = url_key
        return response
