from pathlib import Path

from kash.config.logger import get_logger
from kash.exec import assemble_path_args, kash_command
from kash.exec_model.shell_model import ShellResult
from kash.shell.output.shell_output import cprint
from kash.shell.utils.sys_tool_deps import SysTool, sys_tool_check
from kash.utils.common.parse_shell_args import shell_quote
from kash.utils.errors import InvalidState

log = get_logger(__name__)


@kash_command
def search(
    query_str: str,
    *paths: str,
    sort: str = "path",
    ignore_case: bool = False,
    verbose: bool = False,
) -> ShellResult:
    """
    Search for a string in files at the given paths and return their store paths.
    Useful to find all docs or resources matching a string or regex. This wraps
    ripgrep.

    Example: Look for all resource files containing the string "youtube.com",
    sorted by date modified:

    search "youtube.com" resources/ --sort=modified

    :param sort: How to sort results. Can be `path` or `modified` or `created` (as with `rg`).
    :param ignore_case: Ignore case when searching.
    :param verbose: Also print the ripgrep command line.
    """
    sys_tool_check().require(SysTool.ripgrep)
    from ripgrepy import RipGrepNotFound, Ripgrepy

    resolved_paths = assemble_path_args(*paths)

    strip_prefix = None
    if not resolved_paths:
        resolved_paths = (Path("."),)
        strip_prefix = "./"
    try:
        rg = Ripgrepy(query_str, *[str(p) for p in resolved_paths])
        rg = rg.files_with_matches().sort(sort)
        if ignore_case:
            rg = rg.ignore_case()
        if verbose:
            command = " ".join(
                [shell_quote(arg) for arg in rg.command]
                + [query_str]
                + [str(p) for p in resolved_paths]
            )
            cprint(f"{command}")
        rg_output = rg.run().as_string
        results: list[str] = [
            line.lstrip(strip_prefix) if strip_prefix and line.startswith(strip_prefix) else line
            for line in rg_output.splitlines()
        ]

        return ShellResult(results, show_result=True)
    except RipGrepNotFound:
        raise InvalidState("`rg` command not found. Install ripgrep to use the search command.")
