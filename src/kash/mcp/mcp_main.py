import asyncio
import logging
import time

import anyio
import httpcore
import httpx
from mcp_proxy.sse_client import run_sse_client

from kash.config.init import kash_reload_all
from kash.mcp.mcp_server_routes import publish_mcp_tools
from kash.mcp.mcp_server_stdio import run_mcp_server_stdio

log = logging.getLogger()


def run_standalone():
    # XXX This currently just publishes the tools once. Use the proxy mode to have
    # dynamic publishing of tools.
    kash_reload_all()
    log.warning("Loaded kash, now running in stdio mode")
    publish_mcp_tools()
    run_mcp_server_stdio()


def is_connect_exception(e: BaseException) -> bool:
    if isinstance(e, (httpx.ConnectError, httpcore.ConnectError)):
        return True
    if isinstance(e, BaseExceptionGroup):
        return any(is_connect_exception(exc) for exc in e.exceptions)
    return False


def is_closed_exception(e: BaseException) -> bool:
    # Various kinds of exceptions when input is closed or server is stopped.
    if isinstance(e, ValueError) and "I/O operation on closed file" in str(e):
        return True
    if isinstance(e, anyio.BrokenResourceError):
        return True
    if isinstance(e, BaseExceptionGroup):
        return any(is_closed_exception(exc) for exc in e.exceptions)
    return False


def run_as_proxy(proxy_url: str, timeout_secs: int = 300):
    """
    Run as an stdio proxy to an SSE server. Default timeout 5min in
    case SSE server isn't started at first.
    """
    tries = timeout_secs // 10
    delay = 10
    for _i in range(tries):
        try:
            asyncio.run(run_sse_client(proxy_url))
        except Exception as e:
            if is_closed_exception(e):
                log.warning("Input closed, will retry: %s", proxy_url)
            elif is_connect_exception(e):
                log.warning("Server is not running yet, will retry: %s", proxy_url)
            else:
                log.error(
                    "Error connecting to server, will retry: %s: %s", proxy_url, e, exc_info=True
                )
            time.sleep(delay)

    log.error("Failed to connect. Giving up.")


def run_mcp_server(proxy_to: str | None):
    """
    Run the MCP server, in standalone mode if `proxy_to` is none or else proxying to an SSE
    server if `proxy_to` is set.
    """
    if proxy_to:
        log.warning("Running in proxy mode, connecting to: %s", proxy_to)
        run_as_proxy(proxy_to)
    else:
        log.warning("Running in standalone (stdio) mode")
        run_standalone()
