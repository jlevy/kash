"""
xontrib for fnm (Fast Node Manager) integration with xonsh shell.

Fnm is a good replacement for nvm and is compatible with .nvmrc.

Currently fnm doesn't support xonsh directly. This parses the bash output
of fnm and uses it within xonsh.
"""

import subprocess
from pathlib import Path
from typing import Any, TypedDict

from xonsh.built_ins import XonshSession
from xonsh.events import events


class FnmEnv(TypedDict):
    PATH: str
    FNM_MULTISHELL_PATH: str
    FNM_VERSION_FILE_STRATEGY: str
    FNM_DIR: str
    FNM_LOGLEVEL: str
    FNM_NODE_DIST_MIRROR: str
    FNM_COREPACK_ENABLED: str
    FNM_RESOLVE_ENGINES: str
    FNM_ARCH: str


def parse_fnm_env() -> FnmEnv:
    """
    Parse fnm bash env output into a typed dictionary.
    """
    result = subprocess.run(
        ["fnm", "env", "--use-on-cd", "--shell", "bash"],
        capture_output=True,
        text=True,
        check=True,
    )

    env_vars: FnmEnv = {}  # pyright: ignore
    for line in result.stdout.strip().split("\n"):
        if line.startswith("export "):
            key, value = line.replace("export ", "").split("=", 1)
            env_vars[key] = value.strip('"')

    return env_vars


def apply_fnm_env(xsh: XonshSession, env_vars: FnmEnv) -> None:
    """
    Apply fnm environment variables to xonsh session.
    """
    # Update PATH with multishell bin
    multishell_bin = Path(env_vars["FNM_MULTISHELL_PATH"]) / "bin"
    assert xsh.env is not None
    path = xsh.env["PATH"]
    assert path is not None
    current_paths = [Path(p) for p in path]
    new_paths = [p for p in current_paths if "fnm_multishells" not in str(p)]
    new_paths.insert(0, multishell_bin)
    xsh.env["PATH"] = new_paths

    # Set all other fnm variables
    for key, value in env_vars.items():
        if key != "PATH":
            xsh.env[key] = value


def _nvm_stub(_args: str, _stdin: str, _stdout: str, _stderr: str) -> None:
    print("error: Oops, `nvm` doesn't work in xonsh; try `fnm` instead!")


def _load_xontrib_(xsh: XonshSession, **_) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
    """
    Initialize the fnm xontrib.
    """
    try:
        subprocess.run(["which", "fnm"], capture_output=True, check=True)
    except subprocess.CalledProcessError:
        # Quietly return if fnm is not installed.
        return {}

    try:
        # Set fnm per-session environment variables once at initialization.
        env_vars = parse_fnm_env()
        apply_fnm_env(xsh, env_vars)

        # Name of these args matter since xonsh calls them as keywords.
        def fnm_use_if_file_found(newdir: str, olddir: str | None = None) -> None:  # pyright: ignore
            """
            Check for Node version files and switch if necessary using xsh session.
            """
            version_files = [".node-version", ".nvmrc", "package.json"]
            if any(Path(file).exists() for file in version_files):
                xsh.subproc_uncaptured(["fnm", "use", "--silent-if-unchanged"])

        events.on_chdir(fnm_use_if_file_found)
        fnm_use_if_file_found(".")

        aliases["nvm"] = _nvm_stub  # noqa: F821 # pyright: ignore[reportUndefinedVariable]

        return {}
    except Exception as e:
        print(f"Error initializing fnm xontrib: {e}")
        return {}


def _unload_xontrib_(_xsh: XonshSession, **_) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
    """
    Clean up the fnm xontrib.
    """
    handlers_to_remove = [
        handler
        for handler in events.on_chdir.handlers
        if handler.__name__ == "fnm_use_if_file_found"
    ]
    for handler in handlers_to_remove:
        events.on_chdir.remove(handler)

    return {}
