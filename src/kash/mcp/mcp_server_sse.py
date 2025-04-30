from __future__ import annotations

import asyncio
import threading
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING

from mcp.server.sse import SseServerTransport
from prettyfmt import fmt_path
from sse_starlette.sse import AppStatus
from starlette.applications import Starlette
from starlette.routing import Mount, Route

if TYPE_CHECKING:
    import uvicorn
    from starlette.applications import Starlette

from kash.config.logger import get_logger
from kash.config.server_config import create_server_config
from kash.config.settings import global_settings
from kash.local_server.port_tools import find_available_local_port
from kash.mcp import mcp_server_routes
from kash.utils.errors import InvalidState

log = get_logger(__name__)

MCP_SERVER_NAME = "mcp_server_sse"
MCP_SERVER_HOST = "127.0.0.1"
"""The local hostname to run the MCP SSE server on."""


def create_mcp_app() -> Starlette:
    """Creates the Starlette app wrapped around the base server for SSE transport."""
    app = mcp_server_routes.create_base_server()
    sse = SseServerTransport("/messages/")

    async def handle_sse(request):
        async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
            await app.run(streams[0], streams[1], app.create_initialization_options())

    return Starlette(
        debug=True,
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )


class MCPServerSSE:
    def __init__(self, server_name: str, host: str, log_path: Path):
        self.server_name = server_name
        self.host = host
        self.log_path = log_path
        self.server_lock = threading.RLock()
        self.server_instance: uvicorn.Server | None = None
        self.did_exit = threading.Event()
        self.port: int

    @cached_property
    def app(self) -> Starlette:
        return create_mcp_app()

    @property
    def host_port(self) -> str | None:
        if self.server_instance:
            return f"{self.server_instance.config.host}:{self.server_instance.config.port}"
        else:
            return None

    def _setup_server(self):
        import uvicorn

        # Reset AppStatus.should_exit_event to None to ensure it's created
        # in the correct event loop when needed.
        AppStatus.should_exit_event = None

        port = global_settings().mcp_server_port

        # Check if the port is available.
        try:
            find_available_local_port(self.host, [port])
        except RuntimeError:
            log.warning(
                f"MCP Server port {port} ({self.server_name}) is in use. Will not start another server."
            )
            return False

        self.port = port

        config = create_server_config(self.app, self.host, port, self.server_name, self.log_path)

        server = uvicorn.Server(config)
        self.server_instance = server
        return True

    def _run_server_thread(self):
        assert self.server_instance
        try:
            asyncio.run(self.server_instance.serve())
        except Exception as e:
            log.error("MCP Server failed with error: %s", e)
        finally:
            self.server_instance = None
            self.did_exit.set()

    def start_server(self):
        with self.server_lock:
            if self.server_instance:
                log.warning(
                    "MCP Server already running on: %s",
                    self.host_port,
                )
                return

            self.did_exit.clear()
            if not self._setup_server():
                return

            server_thread = threading.Thread(target=self._run_server_thread, daemon=True)
            server_thread.start()
            log.info("Created new MCP server thread: %s", server_thread)
            log.message(
                "Started server %s on %s with logs to %s",
                self.server_name,
                self.host_port,
                fmt_path(self.log_path),
            )

    def stop_server(self):
        with self.server_lock:
            if not self.server_instance:
                log.warning("MCP Server already stopped.")
                return
            self.server_instance.should_exit = True

            # Wait a few seconds for the server to shut down.
            timeout = 5.0
            if not self.did_exit.wait(timeout=timeout):
                log.warning(
                    "MCP Server did not shut down within %s seconds, forcing exit.", timeout
                )
                self.server_instance.force_exit = True
                if not self.did_exit.wait(timeout=timeout):
                    raise InvalidState(f"MCP Server did not shut down within {timeout} seconds")

            self.server_instance = None
            log.warning("Stopped server %s", self.server_name)

    def restart_server(self):
        self.stop_server()
        self.start_server()


# Singleton instance
_mcp_sse_server = MCPServerSSE(
    MCP_SERVER_NAME, MCP_SERVER_HOST, global_settings().local_server_log_path
)


def start_mcp_server_sse():
    """Start the MCP server in SSE mode."""
    _mcp_sse_server.start_server()


def stop_mcp_server_sse():
    """Stop the SSE server."""
    _mcp_sse_server.stop_server()


def restart_mcp_server_sse():
    """Restart the SSE server."""
    _mcp_sse_server.restart_server()


def run_mcp_server_sse():
    """
    Run server, blocking until shutdown.
    """
    try:
        start_mcp_server_sse()
        _mcp_sse_server.did_exit.wait()
    except KeyboardInterrupt:
        log.warning("Interrupt, shutting down SSE server")
        stop_mcp_server_sse()
    except Exception as e:
        log.error("MCP Server failed: %s", e)
        stop_mcp_server_sse()
        raise  # Re-raise to allow caller to handle fatal errors
