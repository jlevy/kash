import fcntl
import os
import select
import shutil
import subprocess
import sys
import termios
from functools import cache
from pathlib import Path

from kash.config.text_styles import STYLE_HINT
from kash.shell.output.shell_output import cprint
from kash.utils.errors import SetupError


@cache
def terminal_supports_sixel() -> bool:
    """
    Modern terminals that support Sixel should respond with a sequence containing '4'
    in their list of supported features. This is more reliable than checking terminal
    names. Some terminals (like Hyper 4+ with xterm.js 5+) might require explicit
    configuration to enable Sixel support.

    See:
    https://vt100.net/docs/vt510-rm/DA1.html
    https://www.arewesixelyet.com/
    """
    # If not connected to a real terminal the answer is no (and in fact
    # the test below may throw UnsupportedOperation).
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        return False

    # Save the current terminal settings.
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    new_settings = termios.tcgetattr(fd)
    new_settings[3] &= ~(termios.ICANON | termios.ECHO)
    termios.tcsetattr(fd, termios.TCSANOW, new_settings)

    # Set stdin to non-blocking.
    old_flags = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, old_flags | os.O_NONBLOCK)

    try:
        # Send the DA control sequence.
        sys.stdout.write("\x1b[c")
        sys.stdout.flush()

        # Wait for the response.
        ready, _, _ = select.select([fd], [], [], 1)
        if ready:
            response = os.read(fd, 1024).decode()
            # Check if the response indicates SIXEL support.
            return "4" in response
        else:
            return False
    finally:
        # Restore the terminal settings.
        termios.tcsetattr(fd, termios.TCSANOW, old_settings)
        fcntl.fcntl(fd, fcntl.F_SETFL, old_flags)


# Direct detection method. Shouldn't be needed as better method above seems to work.
# @cache
# def terminal_supports_sixel() -> bool:
#     term = os.environ.get("TERM", "")
#     term_program = os.environ.get("TERM_PROGRAM", "")
#     supported_terms = [
#         "xterm",
#         "xterm-256color",
#         "screen.xterm-256color",
#         "kitty",
#         "iTerm.app",
#         "wezterm",
#         "foot",
#         "mlterm",
#     ]
#     term_supports = any(supported_term in term for supported_term in supported_terms)
#     # Old Hyper 3 does not support Sixel, new Hyper 4 does.
#     term_program_supports = term_program not in ["Hyper"]
#     return term_supports and term_program_supports


@cache
def terminal_is_kitty() -> bool:
    return os.environ.get("TERM") == "xterm-kitty"


def _terminal_show_image_sixel(image_path: str | Path, width: int = 600, height: int = 400) -> None:
    if shutil.which("magick") is None:
        raise SetupError("ImageMagick `magick` not found in path; check it is installed?")

    try:
        cmd = [
            "magick",
            str(image_path),
            "-depth",
            "8",
            "-resize",
            f"{width}x{height}",
            "sixel:-",
        ]
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        raise SetupError(f"Failed to display image: {e}")


def _terminal_show_image_kitty(filename: str | Path):
    filename = str(filename)
    try:
        subprocess.run(["kitty", "+kitten", "icat", filename])
    except subprocess.CalledProcessError as e:
        raise SetupError(f"Failed to display image with kitty: {e}")


def terminal_show_image(filename: str | Path):
    """
    Try to display an image in the terminal, using kitty or sixel.
    Raise `SetupError` if not supported.
    """
    if terminal_is_kitty():
        _terminal_show_image_kitty(filename)
    elif terminal_supports_sixel():
        _terminal_show_image_sixel(filename)
    else:
        raise SetupError("Image display in this terminal doesn't seem to be supported")


def terminal_show_image_graceful(filename: str | Path):
    try:
        terminal_show_image(filename)
    except SetupError:
        cprint(f"[Image: {filename}]", style=STYLE_HINT)
