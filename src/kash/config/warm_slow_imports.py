from __future__ import annotations

from funlog import log_calls

from kash.config.logger import get_logger
from kash.utils.common.import_utils import warm_import_library

log = get_logger(__name__)


@log_calls(level="info", show_timing_only=True)
def warm_slow_imports(include_extras: bool = True):
    """
    Pre-import slow packages to avoid delays when they are first used.

    Args:
        include_extras: If True, warm import optional libraries like LLM packages,
                        scipy, torch, etc. Set to False for minimal/faster startup.
    """
    try:
        # Loading actions also loads any kits that are discovered.
        import kash.actions  # noqa: F401
        import kash.local_server  # noqa: F401
        import kash.local_server.local_server  # noqa: F401
        import kash.mcp.mcp_server_sse  # noqa: F401

        # Core libraries that should usually be present
        for lib_name, max_depth in [("xonsh", 3), ("uvicorn", 3)]:
            try:
                warm_import_library(lib_name, max_depth=max_depth)
            except Exception as e:
                log.debug(f"Could not warm import {lib_name}: {e}")

        if include_extras:
            # Fully warm import larger libraries (only if they're installed)
            # These are optional dependencies that may not be present
            optional_libraries = [
                ("pydantic", 5),
                ("litellm", 5),
                ("openai", 5),
                ("torch", 3),  # torch is huge, limit depth
                ("scipy", 3),  # scipy has test modules we want to skip
                ("marker", 4),
                ("pandas", 3),
            ]

            for lib_name, max_depth in optional_libraries:
                try:
                    warm_import_library(lib_name, max_depth=max_depth)
                except Exception as e:
                    log.debug(f"Could not warm import {lib_name}: {e}")

            # Initialize litellm configuration if available
            try:
                from kash.llm_utils.init_litellm import init_litellm

                init_litellm()
            except ImportError:
                pass  # litellm not installed

    except ImportError as e:
        log.warning(f"Error pre-importing packages: {e}")
