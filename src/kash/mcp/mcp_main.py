"""
Command-line launcher for running an MCP server in stdio mode with
kash actions as tools.
"""

import argparse
import logging
import os
from pathlib import Path

from kash.config.init import kash_import_all
from kash.config.logger_basic import basic_logging_setup
from kash.config.settings import LogLevel
from kash.config.setup import setup
from kash.mcp.mcp_server_routes import publish_mcp_tools
from kash.mcp.mcp_server_stdio import get_log_path, run_mcp_server_stdio
from kash.workspaces.workspaces import get_workspace, sandbox_dir


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--workspace",
        default=sandbox_dir(),
        help="Set workspace directory. Defaults to kash sandbox directory.",
    )
    return parser.parse_args()


def main():
    basic_logging_setup(get_log_path(), LogLevel.info)

    log = logging.getLogger()

    args = parse_args()

    base_dir = Path(args.workspace)

    setup(rich_logging=False)
    kash_import_all()

    ws = get_workspace(base_dir, auto_init=True)

    log.info("Running on workspace: %s", ws.base_dir)

    os.chdir(ws.base_dir)

    log.info("Current working directory: %s", Path(".").resolve())

    # FIXME: Make this settable and test dynamic publishing.
    publish_mcp_tools(None)

    run_mcp_server_stdio()


if __name__ == "__main__":
    main()
