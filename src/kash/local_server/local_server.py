from __future__ import annotations

import asyncio
import threading
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import uvicorn
    from fastapi import FastAPI

from prettyfmt import fmt_path

from kash.config.logger import get_logger
from kash.config.server_config import create_server_config
from kash.config.settings import atomic_global_settings, global_settings, local_server_log_path
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


UI_SERVER_NAME = "local_ui_server"
UI_SERVER_HOST = "127.0.0.1"
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
        UI_SERVER_HOST,
        range(
            settings.local_server_ports_start,
            settings.local_server_ports_start + settings.local_server_ports_max,
        ),
    )

    with atomic_global_settings().updates() as settings:
        settings.local_server_port = port

    return port


class LocalServer:
    def __init__(self, server_name: str, host: str, log_path: Path):
        self.server_name = server_name
        self.host = host
        self.log_path = log_path
        self.server_lock = threading.RLock()
        self.did_exit = threading.Event()
        self.server_instance: uvicorn.Server | None = None
        self.port: int

    @cached_property
    def app(self) -> FastAPI:
        return _app_setup()

    @property
    def host_port(self) -> str | None:
        if self.server_instance:
            return f"{self.server_instance.config.host}:{self.server_instance.config.port}"
        else:
            return None

    def _setup_server(self):
        import uvicorn

        port = _pick_port()
        self.port = port
        config = create_server_config(self.app, self.host, port, self.server_name, self.log_path)

        server = uvicorn.Server(config)
        self.server_instance = server

    def _run_server_thread(self):
        assert self.server_instance
        try:
            asyncio.run(self.server_instance.serve())
        except Exception as e:
            log.error("Server failed with error: %s", e)
        finally:
            self.server_instance = None
            self.did_exit.set()

    def start_server(self):
        with self.server_lock:
            if self.server_instance:
                log.warning(
                    "Server already running on: %s",
                    self.host_port,
                )
                return

            self.did_exit.clear()

            self._setup_server()

            server_thread = threading.Thread(target=self._run_server_thread, daemon=True)
            server_thread.start()
            log.info("Created new local server thread: %s", server_thread)
            log.message(
                "Started server %s on %s with logs to %s",
                UI_SERVER_NAME,
                self.host_port,
                fmt_path(self.log_path),
            )

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
            log.warning("Stopped server %s", UI_SERVER_NAME)

    def restart_server(self):
        self.stop_server()
        self.start_server()


# Singleton instance for the UI server.
# Note this is quick to set up (lazy imports).
_ui_server = LocalServer(UI_SERVER_NAME, UI_SERVER_HOST, local_server_log_path())


def start_ui_server():
    _ui_server.start_server()


def stop_ui_server():
    _ui_server.stop_server()


def restart_ui_server():
    _ui_server.restart_server()
