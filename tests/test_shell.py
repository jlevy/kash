from kash.commands.base.general_commands import self_check
from kash.shell.shell_main import run_shell


def test_self_check():
    self_check()
    run_shell("self_check")  # Also confirm shell runs.
