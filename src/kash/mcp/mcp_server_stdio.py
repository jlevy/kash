import asyncio
import logging

from mcp.server.stdio import stdio_server

from kash.config.settings import server_log_file_path
from kash.mcp import mcp_server_routes

log = logging.getLogger(__name__)

MCP_SERVER_NAME = "kash_mcp_server"


def get_log_path():
    return server_log_file_path(MCP_SERVER_NAME, "stdio")


def run_mcp_server_stdio():
    """
    Runs the MCP server in stdio mode, blocking until completion.
    """

    async def arun():
        log.info("Starting MCP server in stdio mode")
        async with stdio_server() as (read_stream, write_stream):
            # Uses the same base server as the SSE version
            server = mcp_server_routes.create_base_server()
            await server.run(read_stream, write_stream, server.create_initialization_options())

    try:
        # For stdio mode, we just run until completion.
        asyncio.run(arun())
    except Exception as e:
        log.error("MCP Server (stdio) failed with error: %s", e)
        log.exception("Full exception details:")
