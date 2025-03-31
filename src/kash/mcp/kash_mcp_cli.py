"""
Command-line launcher for running an MCP server. By default,
expects kash to be running separately
"""

import argparse
import asyncio
import logging
import os
import time
from pathlib import Path

import anyio
import httpcore
import httpx
from mcp_proxy.sse_client import run_sse_client
from rich_argparse.contrib import ParagraphRichHelpFormatter

from kash.config.init import kash_reload_all
from kash.config.logger_basic import basic_logging_setup
from kash.config.settings import APP_NAME, GLOBAL_LOGS_DIR, MCP_SERVER_PORT, LogLevel
from kash.config.setup import setup
from kash.mcp.mcp_server_routes import publish_mcp_tools
from kash.mcp.mcp_server_sse import MCP_LOG_PREFIX
from kash.mcp.mcp_server_stdio import run_mcp_server_stdio
from kash.shell.version import get_version
from kash.workspaces.workspaces import Workspace, get_ws, global_ws_dir

__version__ = get_version()

APP_VERSION = f"{APP_NAME} {__version__}"

DEFAULT_PROXY_URL = f"http://localhost:{MCP_SERVER_PORT}/sse"

LOG_PATH = GLOBAL_LOGS_DIR / f"{MCP_LOG_PREFIX}_cli.log"

basic_logging_setup(LOG_PATH, LogLevel.info)

log = logging.getLogger()


def parse_args():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=ParagraphRichHelpFormatter
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--workspace",
        default=global_ws_dir(),
        help="Set workspace directory. Defaults to kash global workspace directory.",
    )
    parser.add_argument(
        "--proxy",
        action="store_true",
        help="Run in proxy mode, expecting kash to already be running in SSE mode in another local process.",
    )
    parser.add_argument(
        "--proxy_url",
        type=str,
        help=(
            "URL for proxy mode. Usually you can omit this as it will by default connect to the "
            f"default kash sse server: {DEFAULT_PROXY_URL}"
        ),
    )
    return parser.parse_args()


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


def connect_to_sse_server(proxy_url: str):
    # Try for 5 minutes
    tries = 30
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


def main():
    args = parse_args()

    base_dir = Path(args.workspace)

    setup(rich_logging=False)

    log.warning("kash MCP CLI started, logging to: %s", LOG_PATH)
    log.warning("Current working directory: %s", Path(".").resolve())

    if args.proxy:
        proxy_url = args.proxy_url or DEFAULT_PROXY_URL
        log.warning("Connecting to proxy server at: %s", proxy_url)

        connect_to_sse_server(proxy_url)
    else:
        ws: Workspace = get_ws(name_or_path=base_dir, auto_init=True)
        os.chdir(ws.base_dir)
        log.warning("Running in workspace: %s", ws.base_dir)

        run_standalone()


if __name__ == "__main__":
    main()
