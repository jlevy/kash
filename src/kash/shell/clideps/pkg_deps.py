import logging
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from cachetools import TTLCache, cached
from rich.console import Group
from rich.text import Text

from kash.config.text_styles import EMOJI_WARN
from kash.shell.clideps.platforms import PLATFORM, Platform
from kash.shell.output.shell_formatting import format_name_and_value, format_success_or_failure
from kash.shell.output.shell_output import cprint
from kash.utils.errors import SetupError

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class PkgDep:
    """
    Information about a system tool dependency and how to install it.
    """

    command_names: tuple[str, ...]
    check_function: Callable[[], bool] | None = None
    comment: str | None = None
    warn_if_missing: bool = False

    brew_pkg: str | None = None
    apt_pkg: str | None = None
    pip_pkg: str | None = None
    winget_pkg: str | None = None


def check_libmagic():
    try:
        import magic

        magic.Magic()
        return True
    except Exception as e:
        log.info("libmagic is not installed or not accessible: %s", e)
        return False


class Pkg(Enum):
    """
    External (usually non-Python) system tools that we like to use.
    """

    # These are usually pre-installed on all platforms:
    less = PkgDep(("less",))
    tail = PkgDep(("tail",))

    bat = PkgDep(
        ("batcat", "bat"),  # batcat for Debian/Ubuntu), bat for macOS
        brew_pkg="bat",
        apt_pkg="bat",
        winget_pkg="sharkdp.bat",
        warn_if_missing=True,
    )
    ripgrep = PkgDep(
        ("rg",),
        brew_pkg="ripgrep",
        apt_pkg="ripgrep",
        winget_pkg="BurntSushi.ripgrep",
        warn_if_missing=True,
    )
    eza = PkgDep(
        ("eza",),
        brew_pkg="eza",
        apt_pkg="eza",
        winget_pkg="eza-community.eza",
        warn_if_missing=True,
    )
    zoxide = PkgDep(
        ("zoxide",),
        brew_pkg="zoxide",
        apt_pkg="zoxide",
        winget_pkg="ajeetdsouza.zoxide",
        warn_if_missing=True,
    )
    hexyl = PkgDep(
        ("hexyl",),
        brew_pkg="hexyl",
        apt_pkg="hexyl",
        winget_pkg="sharkdp.hexyl",
        warn_if_missing=True,
    )
    pygmentize = PkgDep(
        ("pygmentize",),
        brew_pkg="pygments",
        apt_pkg="python3-pygments",
        pip_pkg="Pygments",
    )
    libmagic = PkgDep(
        (),
        comment="""
          For macOS and Linux, brew or apt gives the latest binaries. For Windows, it may be
          easier to use pip.
        """,
        check_function=check_libmagic,
        brew_pkg="libmagic",
        apt_pkg="libmagic1",
        pip_pkg="python-magic-bin",
        warn_if_missing=True,
    )
    ffmpeg = PkgDep(
        ("ffmpeg",),
        brew_pkg="ffmpeg",
        apt_pkg="ffmpeg",
        winget_pkg="Gyan.FFmpeg",
        warn_if_missing=True,
    )
    imagemagick = PkgDep(
        ("magick",),
        brew_pkg="imagemagick",
        apt_pkg="imagemagick",
        winget_pkg="ImageMagick.ImageMagick",
        warn_if_missing=True,
    )

    @property
    def full_name(self) -> str:
        name = self.name
        if self.value.command_names:
            name += f" ({' or '.join(f'`{name}`' for name in self.value.command_names)})"
        return name


@dataclass(frozen=True)
class InstalledPkgs:
    """
    Info about which tools are installed.
    """

    tools: dict[Pkg, str | bool]

    def has(self, *tools: Pkg) -> bool:
        return all(self.tools[tool] for tool in tools)

    def require(self, *tools: Pkg) -> None:
        for tool in tools:
            if not self.has(tool):
                print_missing_tool_help(tool)
                raise SetupError(
                    f"`{tool.value}` ({tool.value.command_names}) needed but not found"
                )

    def missing_tools(self, *tools: Pkg) -> list[Pkg]:
        if not tools:
            tools = tuple(Pkg)
        return [tool for tool in tools if not self.tools[tool]]

    def warn_if_missing(self, *tools: Pkg) -> None:
        for tool in self.missing_tools(*tools):
            if tool.value.warn_if_missing:
                print_missing_tool_help(tool)

    def formatted(self) -> Group:
        texts: list[Text | Group] = []
        for tool, path in self.items():
            found_str = "Found" if isinstance(path, bool) else f"Found: `{path}`"
            doc = format_success_or_failure(
                bool(path),
                true_str=format_name_and_value(tool.name, found_str),
                false_str=format_name_and_value(tool.name, "Not found!"),
            )
            texts.append(doc)

        return Group(*texts)

    def items(self) -> list[tuple[Pkg, str | bool]]:
        return sorted(self.tools.items(), key=lambda item: item[0].name)

    def status(self) -> Text:
        texts: list[Text] = []
        for tool, path in self.items():
            texts.append(format_success_or_failure(bool(path), tool.name))

        return Text.assemble("Local system tools found: ", Text(" ").join(texts))


def print_missing_tool_help(tool: Pkg):
    warn_str = f"{EMOJI_WARN} {tool.full_name} was not found; it is recommended to install it for better functionality."
    if tool.value.comment:
        warn_str += f" {tool.value.comment}"
    install_str = get_install_suggestion(tool)
    if install_str:
        warn_str += f" {install_str}"

    cprint(warn_str)


def get_install_suggestion(*missing_tools: Pkg) -> str | None:
    brew_pkgs = [tool.value.brew_pkg for tool in missing_tools if tool.value.brew_pkg]
    apt_pkgs = [tool.value.apt_pkg for tool in missing_tools if tool.value.apt_pkg]
    winget_pkgs = [tool.value.winget_pkg for tool in missing_tools if tool.value.winget_pkg]
    pip_pkgs = [tool.value.pip_pkg for tool in missing_tools if tool.value.pip_pkg]

    if PLATFORM == Platform.Darwin and brew_pkgs:
        return "On macOS, try using Homebrew: `brew install %s`" % " ".join(brew_pkgs)
    elif PLATFORM == Platform.Linux and apt_pkgs:
        return "On Linux, try using your package manager, e.g.: `sudo apt install %s`" % " ".join(
            apt_pkgs
        )
    elif PLATFORM == Platform.Windows and winget_pkgs:
        return "On Windows, try using Winget: `winget install %s`" % " ".join(winget_pkgs)

    if pip_pkgs:
        return "You may also try using pip: `pip install %s`" % " ".join(pip_pkgs)


@cached(TTLCache(maxsize=1, ttl=5.0))
def pkg_check() -> InstalledPkgs:
    """
    Check which third-party tools are installed.
    """
    tools: dict[Pkg, str | bool] = {}

    def which_tool(tool: Pkg) -> str | None:
        return next(filter(None, (shutil.which(name) for name in tool.value.command_names)), None)

    def check_tool(tool: Pkg) -> bool:
        return bool(tool.value.check_function and tool.value.check_function())

    for tool in Pkg:
        tools[tool] = which_tool(tool) or check_tool(tool)

    return InstalledPkgs(tools)
