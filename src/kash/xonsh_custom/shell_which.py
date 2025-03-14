import builtins
import os
import sys
from pathlib import Path
from typing import cast

from cachetools import TTLCache, cached
from xonsh.built_ins import XSH


def current_full_path() -> list[str]:
    """
    XSH path might contain additional items (e.g. npm). So merge.
    """
    xsh_path: list[str] = []
    if XSH.env:
        xsh_path = cast(list[str], XSH.env.get("PATH"))
    env_path = os.environ.get("PATH", "").split(os.pathsep)
    if sys.platform.startswith("win"):
        env_path.insert(0, os.curdir)  # implied by Windows shell
    return xsh_path + [p for p in env_path if p not in xsh_path]


@cached(TTLCache(maxsize=1000, ttl=60))
def is_valid_command(command_name: str, path: list[str] | None = None) -> bool:
    """
    Is this a valid command xonsh will understand, given current path
    and all loaded commands?
    """

    from xonsh.xoreutils._which import WhichError, which

    if not path:
        path = current_full_path()

    # Built-in values and aliases are allowed.
    python_builtins = dir(builtins)
    xonsh_builtins = dir(XSH.builtins)
    globals = XSH.ctx
    aliases = XSH.aliases or {}
    if (
        command_name in python_builtins
        or command_name in xonsh_builtins
        or command_name in globals
        or command_name in aliases
    ):
        return True

    # Directories are allowed since we have auto-cd on.
    if Path(command_name).is_dir():
        return True

    # Finally check if it is a known command.
    try:
        which(command_name, path=path)
        if command_name.lower() != command_name:
            # XXX A tricky thing is macOS's case insensitive filesystems means `which What`
            # returns `/usr/bin/What` (preserving and matching capital letters). This is silly
            # and we don't consider that a match.
            return False
        else:
            return True
    except WhichError:
        return False
