"""
Welcome to Kash! This command is the main way to run the kash shell.

Usually this is used to start the kash interactively but you can also pass a single
command to run non-interactively.

Run `kash manual` for general help. Run `kash self_check` to check the kash environment.
Run `kash --help` for this page.

More information at: github.com/jlevy/kash
"""

import argparse
import threading

from strif import quote_if_needed

from kash.config.logger import get_console, get_logger
from kash.config.setup import kash_setup
from kash.shell.version import get_full_version_name, get_version

kash_setup(rich_logging=True)  # Set up logging first.

log = get_logger(__name__)


__version__ = get_version()


# No longer using, but keeping for reference.
def run_plain_xonsh():
    """
    The standard way to run kash is now via the customized shell.
    But we can also run a regular xonsh shell and have it load kash commands via the
    xontrib only (in ~/.xonshrc), but the full customizations of prompts, tab
    completion, etc are not available.
    """
    import xonsh.main

    from kash.xonsh_custom.custom_shell import install_to_xonshrc

    install_to_xonshrc()
    xonsh.main.main()


# Event to monitor loading.
shell_ready_event = threading.Event()

imports_done_event = threading.Event()


def run_shell(single_command: str | None = None):
    """
    Run the kash shell interactively or non-interactively with a single command.
    """
    from kash.xonsh_custom.custom_shell import start_shell

    start_shell(single_command, shell_ready_event)


def build_parser() -> argparse.ArgumentParser:
    from clideps.utils.readable_argparse import ReadableColorFormatter

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=ReadableColorFormatter)

    # Don't call get_full_version_name() here, as it's slow.
    parser.add_argument("--version", action="store_true", help="show version and exit")

    return parser


def _import_packages():
    from kash.config.warm_slow_imports import warm_slow_imports

    warm_slow_imports(include_extras=False)

    imports_done_event.set()


def import_with_status_if_slow(min_time: float = 1.0):
    """
    Not required, but imports can be remarkably slow the first time, so this shows a status message.
    """

    # Start imports in background thread
    import_thread = threading.Thread(target=_import_packages, daemon=True)
    import_thread.start()

    # Wait for imports to complete, with a short timeout
    if not imports_done_event.wait(timeout=min_time):
        # If imports aren't done quickly, show status message
        if get_console().is_terminal:
            with get_console().status(
                "Importing packages (this is a bit slow the first time) …", spinner="line"
            ):
                import_thread.join()
    else:
        import_thread.join()


def main():
    parser = build_parser()

    args, unknown = parser.parse_known_args()

    if args.version:
        print(get_full_version_name(with_kits=True))
        return

    # Join remaining arguments to pass as a single command to kash.
    # Use Python-style quoting only if needed for xonsh.
    single_command = None
    if unknown:
        single_command = " ".join(quote_if_needed(arg) for arg in unknown)

    import_with_status_if_slow()

    run_shell(single_command)


if __name__ == "__main__":
    main()
