from __future__ import annotations

import asyncio
import threading
from functools import cached_property
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import uvicorn
    from fastapi import FastAPI

from prettyfmt import fmt_path

from kash.config.logger import get_logger
from kash.config.server_config import create_server_config
from kash.config.settings import atomic_global_settings, global_settings, server_log_file_path
from kash.local_server import local_server_routes
from kash.local_server.port_tools import find_available_local_port
from kash.utils.errors import InvalidInput, InvalidState

log = get_logger(__name__)


def _app_setup() -> FastAPI:
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse

    app = FastAPI()

    app.include_router(local_server_routes.router)

    # Map common exceptions to HTTP codes.
    # FileNotFound first, since it might also be an InvalidInput.
    @app.exception_handler(FileNotFoundError)
    async def file_not_found_exception_handler(_request: Request, exc: FileNotFoundError):
        return JSONResponse(
            status_code=404,
            content={"message": f"File not found: {exc}"},
        )

    @app.exception_handler(InvalidInput)
    async def invalid_input_exception_handler(_request: Request, exc: InvalidInput):
        return JSONResponse(
            status_code=400,
            content={"message": f"Invalid input: {exc}"},
        )

    # Global exception handler.
    @app.exception_handler(Exception)
    async def global_exception_handler(_request: Request, _exc: Exception):
        return JSONResponse(
            status_code=500,
            content={"message": "Internal server error."},
        )

    return app


LOCAL_SERVER_NAME = "local_server"
LOCAL_SERVER_HOST = "127.0.0.1"
"""
The local hostname to run the local server on.

Important: This should be the loopback address, since this local server has full access
to the local machine and filesystem!
"""


def _pick_port() -> int:
    """
    Pick an available port for the local server and update the global settings.
    """
    settings = global_settings()
    port = find_available_local_port(
        LOCAL_SERVER_HOST,
        range(
            settings.local_server_ports_start,
            settings.local_server_ports_start + settings.local_server_ports_max,
        ),
    )

    with atomic_global_settings().updates() as settings:
        settings.local_server_port = port

    return port


class LocalServer:
    def __init__(self):
        self.server_lock = threading.RLock()
        self.server_instance: uvicorn.Server | None = None
        self.did_exit = threading.Event()

    @cached_property
    def app(self) -> FastAPI:
        return _app_setup()

    def _run_server(self):
        import uvicorn

        port = _pick_port()
        self.log_path = server_log_file_path(LOCAL_SERVER_NAME, port)

        config = create_server_config(
            self.app, LOCAL_SERVER_HOST, port, LOCAL_SERVER_NAME, self.log_path
        )
        with self.server_lock:
            server = uvicorn.Server(config)
            self.server_instance = server

        async def serve():
            try:
                log.message(
                    "Starting local server on %s:%s",
                    LOCAL_SERVER_HOST,
                    port,
                )
                log.message("Local server logs: %s", fmt_path(server_log_file_path(port)))
                await server.serve()
            finally:
                self.did_exit.set()

        try:
            asyncio.run(serve())
        except Exception as e:
            log.error("Server failed with error: %s", e)
        finally:
            with self.server_lock:
                self.server_instance = None

    def start_server(self):
        with self.server_lock:
            if self.server_instance:
                log.warning(
                    "Server already running on %s:%s.",
                    self.server_instance.config.host,
                    self.server_instance.config.port,
                )
                return

            self.did_exit.clear()
            server_thread = threading.Thread(target=self._run_server, daemon=True)
            server_thread.start()
            log.info("Created new local server thread: %s", server_thread)

    def stop_server(self):
        with self.server_lock:
            if not self.server_instance:
                log.warning("Server already stopped.")
                return
            self.server_instance.should_exit = True

            # Wait a few seconds for the server to shut down.
            timeout = 5.0
            if not self.did_exit.wait(timeout=timeout):
                log.warning("Server did not shut down within %s seconds, forcing exit.", timeout)
                self.server_instance.force_exit = True
                if not self.did_exit.wait(timeout=timeout):
                    raise InvalidState(f"Server did not shut down within {timeout} seconds")

            self.server_instance = None
            log.warning("Server stopped.")

    def restart_server(self):
        self.stop_server()
        self.start_server()


# Singleton instance.
# Note this is quick to set up (lazy import).
_local_server = LocalServer()


def start_local_server():
    _local_server.start_server()


def stop_local_server():
    _local_server.stop_server()


def restart_local_server():
    _local_server.restart_server()
