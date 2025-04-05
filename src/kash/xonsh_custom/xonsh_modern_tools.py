import subprocess

from xonsh.built_ins import XSH
from xonsh.xontribs import xontribs_load

from kash.config.settings import global_settings
from kash.shell.clideps.pkg_deps import Pkg, pkg_check


def modernize_shell() -> None:
    """
    Add some basic aliases and tools to improve and modernize the xonsh shell
    experience, if they are installed.
    """
    add_fnm()
    enable_zoxide()
    add_aliases()


def add_fnm() -> None:
    # Another convenience xontrib (fnm, since nvm doesn't work in xonsh).
    xontribs_load(["kash.xontrib.fnm"], full_module=True)


def enable_zoxide() -> None:
    installed_tools = pkg_check()

    if installed_tools.has(Pkg.zoxide):
        assert XSH.builtins
        zoxide_init = subprocess.check_output(["zoxide", "init", "xonsh"]).decode()
        XSH.builtins.execx(zoxide_init, "exec", XSH.ctx, filename="zoxide")


def add_aliases() -> None:
    installed_tools = pkg_check()

    assert XSH.aliases
    if installed_tools.has(Pkg.eza):
        if global_settings().use_nerd_icons:
            icons = ["--icons"]
        else:
            icons = []

        XSH.aliases["ls"] = ["eza", "--group-directories-first", "-F", *icons]
        XSH.aliases["ll"] = ["eza", "--group-directories-first", "-F", "-l", *icons]
        XSH.aliases["lla"] = ["eza", "--group-directories-first", "-F", "-la", *icons]


# TODO:
# - find -> fd
# - cat -> bat
# - grep -> rg
# - du -> dust
# - df -> duf
# - ps -> procs
# - top -> btm
