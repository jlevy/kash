import asyncio
from enum import Enum
import logging
import time
from typing import Literal

import anyio
import httpcore
import httpx
from mcp_proxy.sse_client import run_sse_client

from kash.config.init import kash_reload_all
from kash.mcp.mcp_server_routes import publish_mcp_tools
from kash.mcp.mcp_server_sse import run_mcp_server_sse
from kash.mcp.mcp_server_stdio import run_mcp_server_stdio

log = logging.getLogger()


class McpMode(Enum):
    standalone_stdio = "standalone_stdio"
    """Run standalone, with all tools loaded, as stdio server."""

    standalone_sse = "standalone_sse"
    """Run standalone, with all tools loaded, as SSE server."""

    proxy_stdio = "proxy_stdio"
    """Run as a proxy, in stdio mode, connecting to an SSE server."""


def run_as_proxy(proxy_to_url: str, timeout_secs: int = 300):
    """
    Run as an stdio proxy to an SSE server. Default timeout 5min in
    case SSE server isn't started at first.
    """
    tries = timeout_secs // 10
    delay = 10
    for _i in range(tries):
        try:
            asyncio.run(run_sse_client(proxy_to_url))
        except Exception as e:
            if is_closed_exception(e):
                log.warning("Input closed, will retry: %s", proxy_to_url)
            elif is_connect_exception(e):
                log.warning("Server is not running yet, will retry: %s", proxy_to_url)
            else:
                log.error(
                    "Error connecting to server, will retry: %s: %s", proxy_to_url, e, exc_info=True
                )
            time.sleep(delay)

    log.error("Failed to connect. Giving up.")


def run_mcp_server(mcp_mode: McpMode, proxy_to: str | None):
    """
    Run an MCP server in one of the given modes.
    """
    if mcp_mode == McpMode.proxy_stdio:
        if not proxy_to:
            raise ValueError("Must specify `proxy_to` for proxy mode")
        log.warning("Running in proxy mode, connecting to: %s", proxy_to)
        run_as_proxy(proxy_to)
    else:
        # XXX This currently just publishes the tools once. Use the proxy mode to have
        # dynamic publishing of tools.
        log.warning("Running MCP server standalone, starting up...")
        kash_reload_all()
        publish_mcp_tools()
        log.warning("Loaded kash, now running MCP server server (%s)", mcp_mode)
        if mcp_mode == McpMode.standalone_stdio:
            run_mcp_server_stdio()
        else:
            run_mcp_server_sse()


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
