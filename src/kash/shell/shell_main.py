"""
Welcome to kash! Main way to run the kash shell.

Usually this is used to start the kash interactively but you can also pass a single
command to run non-interactively.

Run `kash manual` for general help. Run `kash self_check` to check the kash environment.
Run `kash --help` for this page.

More information at: github.com/jlevy/kash
"""

import argparse
import threading

import xonsh.main
from strif import quote_if_needed

from kash.config.setup import setup
from kash.shell.utils.argparse_utils import WrappedColorFormatter
from kash.shell.version import get_full_version_name, get_version
from kash.xonsh_custom.custom_shell import install_to_xonshrc, start_shell

setup(rich_logging=True)  # Set up logging first.


__version__ = get_version()


# No longer using, but keeping for reference.
def run_plain_xonsh():
    """
    The standard way to run kash is now via the customized shell.
    But we can also run a regular xonsh shell and have it load kash commands via the
    xontrib only (in ~/.xonshrc), but the full customizations of prompts, tab
    completion, etc are not available.
    """
    install_to_xonshrc()
    xonsh.main.main()


# Event to monitor loading.
shell_ready_event = threading.Event()


def run_shell(single_command: str | None = None):
    """
    Run the kash shell interactively or non-interactively with a single command.
    """
    start_shell(single_command, shell_ready_event)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=WrappedColorFormatter)

    parser.add_argument("--version", action="version", version=get_full_version_name())

    return parser


def main():
    parser = build_parser()
    _args, unknown = parser.parse_known_args()

    # Join remaining arguments to pass as a single command to kash.
    # Use Python-style quoting only if needed for xonsh.
    single_command = None
    if unknown:
        single_command = " ".join(quote_if_needed(arg) for arg in unknown)

    run_shell(single_command)


if __name__ == "__main__":
    main()
