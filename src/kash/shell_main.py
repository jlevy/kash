import sys
from typing import Optional

import xonsh.main

# Keeping initial imports/deps minimal.
from kash.config.logger import get_logger
from kash.config.settings import APP_NAME
from kash.config.setup import setup
from kash.version import get_version
from kash.xonsh_custom.custom_shell import install_to_xonshrc, start_shell

setup(rich_logging=True)  # Set up logging first.

log = get_logger(__name__)

__version__ = get_version()

APP_VERSION = f"{APP_NAME} {__version__}"

# If true use the kash-customized xonsh shell. This is the standard way to run kash since
# it then supports custom parsing of shell input to include LLM-based assistance, etc.
# Alternatively, we can run a regular xonsh shell and have it load kash commands via the
# xontrib only (in ~/.xonshrc) but this is not preferred.
CUSTOMIZE_XONSH = True


def run_shell(single_command: Optional[str] = None):
    if CUSTOMIZE_XONSH:
        start_shell(single_command)
    else:
        # For a more basic xonsh init without a customized shell.
        # This isn't recommended since some features aren't available.
        # When running in regular xonsh we need to load kash xontrib via xonshrc.
        install_to_xonshrc()
        xonsh.main.main()


def parse_args() -> Optional[str]:
    # Do our own arg parsing since everything except these two options
    # should be handled as a kash command.
    if sys.argv[1:] == ["--version"]:
        print(APP_VERSION)
        sys.exit(0)
    elif sys.argv[1:] == ["--help"]:
        from kash.commands.help_commands import help_commands

        help_commands.manual()
        sys.exit(0)
    elif len(sys.argv) > 1 and sys.argv[1].startswith("-"):
        print(f"Unrecognized option: {sys.argv[1]}", file=sys.stderr)
        sys.exit(2)

    # Everything else is a kash command so passed to the shell.
    return " ".join(sys.argv[1:]) if len(sys.argv) > 1 else None


def main():
    """
    Main entry point for kash shell.
    Uses customized xonsh shell.
    """
    command = parse_args()
    run_shell(command)


if __name__ == "__main__":
    main()
