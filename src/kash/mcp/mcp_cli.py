"""
Command-line launcher for running an MCP server. By default runs in stdio
standalone mode, with all kash tools exposed. But can be run in SSE standalone
mode or as a stdio proxy to another SSE server.
"""

import argparse
import logging
import os
from pathlib import Path

from kash.config.logger_basic import basic_logging_setup
from kash.config.settings import DEFAULT_MCP_SERVER_PORT, GLOBAL_LOGS_DIR, LogLevel
from kash.config.setup import setup
from kash.mcp.mcp_main import McpMode, run_mcp_server
from kash.mcp.mcp_server_sse import MCP_LOG_PREFIX
from kash.shell.utils.argparse_utils import WrappedColorFormatter
from kash.shell.version import get_version
from kash.workspaces.workspaces import Workspace, get_ws, global_ws_dir

__version__ = get_version()

DEFAULT_PROXY_URL = f"http://localhost:{DEFAULT_MCP_SERVER_PORT}/sse"

LOG_PATH = GLOBAL_LOGS_DIR / f"{MCP_LOG_PREFIX}_cli.log"

basic_logging_setup(LOG_PATH, LogLevel.info)

log = logging.getLogger()


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=WrappedColorFormatter)
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--workspace",
        default=global_ws_dir(),
        help=f"Set workspace directory. Defaults to kash global workspace directory: {global_ws_dir()}",
    )
    parser.add_argument(
        "--proxy",
        action="store_true",
        help="Run in proxy mode, expecting kash to already be running in SSE mode on another local process",
    )
    parser.add_argument(
        "--proxy_url",
        type=str,
        help=(
            "URL for proxy mode. If you are running kash locally, you can omit this and use the default SSE server: "
            f"{DEFAULT_PROXY_URL}"
        ),
    )
    parser.add_argument("--sse", action="store_true", help="Run in SSE standalone mode")
    return parser


def main():
    args = build_parser().parse_args()

    base_dir = Path(args.workspace)

    setup(rich_logging=False)

    log.warning("kash MCP CLI started, logging to: %s", LOG_PATH)
    log.warning("Current working directory: %s", Path(".").resolve())

    ws: Workspace = get_ws(name_or_path=base_dir, auto_init=True)
    os.chdir(ws.base_dir)
    log.warning("Running in workspace: %s", ws.base_dir)

    mcp_mode = (
        McpMode.standalone_sse
        if args.sse
        else McpMode.proxy_stdio
        if args.proxy
        else McpMode.standalone_stdio
    )
    proxy_to = args.proxy_url or DEFAULT_PROXY_URL if mcp_mode == McpMode.proxy_stdio else None
    run_mcp_server(mcp_mode, proxy_to=proxy_to)


if __name__ == "__main__":
    main()
