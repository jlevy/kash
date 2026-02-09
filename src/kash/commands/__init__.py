from __future__ import annotations

from pathlib import Path

from kash.exec.importing import import_and_register

_PACKAGE_NAME = __package__
_PARENT_DIR = Path(__file__).parent

_commands_registered = False


def ensure_commands_registered() -> None:
    """
    Register all built-in commands. Idempotent — safe to call multiple times.
    Called automatically by `get_all_commands()`.
    """
    global _commands_registered
    if _commands_registered:
        return
    _commands_registered = True
    import_and_register(
        _PACKAGE_NAME,
        _PARENT_DIR,
        ["base", "extras", "help", "workspace"],
    )
