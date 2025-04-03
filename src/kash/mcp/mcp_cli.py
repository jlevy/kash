"""
Command-line launcher for running an MCP server. By default,
expects kash to be running separately
"""

import argparse
import logging
import os
from pathlib import Path

from kash.config.logger_basic import basic_logging_setup
from kash.config.settings import GLOBAL_LOGS_DIR, MCP_SERVER_PORT, LogLevel
from kash.config.setup import setup
from kash.mcp.mcp_main import run_mcp_server
from kash.mcp.mcp_server_sse import MCP_LOG_PREFIX
from kash.shell.utils.argparse_utils import WrappedColorFormatter
from kash.shell.version import get_version
from kash.workspaces.workspaces import Workspace, get_ws, global_ws_dir

__version__ = get_version()

DEFAULT_PROXY_URL = f"http://localhost:{MCP_SERVER_PORT}/sse"

LOG_PATH = GLOBAL_LOGS_DIR / f"{MCP_LOG_PREFIX}_cli.log"

basic_logging_setup(LOG_PATH, LogLevel.info)

log = logging.getLogger()


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=WrappedColorFormatter)
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


def main():
    args = parse_args()

    base_dir = Path(args.workspace)

    setup(rich_logging=False)

    log.warning("kash MCP CLI started, logging to: %s", LOG_PATH)
    log.warning("Current working directory: %s", Path(".").resolve())

    ws: Workspace = get_ws(name_or_path=base_dir, auto_init=True)
    os.chdir(ws.base_dir)
    log.warning("Running in workspace: %s", ws.base_dir)

    proxy_url = args.proxy_url or DEFAULT_PROXY_URL
    run_mcp_server(proxy_to=proxy_url if args.proxy else None)


if __name__ == "__main__":
    main()
