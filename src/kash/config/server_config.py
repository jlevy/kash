from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import uvicorn


def create_server_config(
    app: Callable[..., Any], host: str, port: int, server_name: str, log_path: Path
) -> "uvicorn.Config":
    """
    Create a common server configuration for both local and MCP servers.
    `app` can be a FastAPI or Starlette app.
    """
    import uvicorn

    import kash.config.suppress_warnings  # noqa: F401

    return uvicorn.Config(
        app,
        host=host,
        port=port,
        log_config={
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                }
            },
            "handlers": {
                "default": {
                    "formatter": "default",
                    "class": "logging.FileHandler",
                    "filename": str(log_path),
                }
            },
            "loggers": {
                # Commenting this out so we don't affect the root logger:
                # "": {"handlers": ["default"], "level": "INFO"},
                "uvicorn": {"handlers": ["default"], "level": "INFO", "propagate": False},
                "uvicorn.error": {"handlers": ["default"], "level": "INFO", "propagate": False},
                "uvicorn.access": {"handlers": ["default"], "level": "INFO", "propagate": False},
                f"kash.{server_name}": {
                    "handlers": ["default"],
                    "level": "INFO",
                    "propagate": False,
                },
            },
        },
    )
