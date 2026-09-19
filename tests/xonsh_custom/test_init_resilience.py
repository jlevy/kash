"""Startup and prompt failures must not take down the shell."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from kash.xonsh_custom.load_into_xonsh import load_into_xonsh, recover_from_init_failure


def test_recover_from_init_failure_installs_prompt():
    with patch("kash.xonsh_custom.load_into_xonsh._install_prompt") as install:
        recover_from_init_failure(RuntimeError("init exploded"))
        assert install.called


def test_recover_from_init_failure_survives_prompt_install_error():
    with patch(
        "kash.xonsh_custom.load_into_xonsh._install_prompt",
        side_effect=RuntimeError("env exploded"),
    ):
        recover_from_init_failure(RuntimeError("init exploded"))


def test_load_into_xonsh_survives_workspace_and_setup_errors():
    with (
        patch("kash.xonsh_custom.load_into_xonsh.is_interactive", return_value=True),
        patch("kash.xonsh_custom.load_into_xonsh.welcome", side_effect=RuntimeError("welcome")),
        patch(
            "kash.xonsh_custom.load_into_xonsh._shell_interactive_setup",
            side_effect=RuntimeError("setup"),
        ),
        patch("kash.xonsh_custom.load_into_xonsh._install_prompt") as install,
        patch(
            "kash.xonsh_custom.load_into_xonsh.reload_shell_commands_and_actions",
            side_effect=RuntimeError("commands"),
        ),
        patch("kash.xonsh_custom.load_into_xonsh.self_check", side_effect=RuntimeError("check")),
        patch(
            "kash.xonsh_custom.load_into_xonsh.start_mcp_server",
            side_effect=RuntimeError("mcp"),
        ),
        patch("kash.xonsh_custom.load_into_xonsh.current_ws", side_effect=RuntimeError("ws")),
        patch("kash.xonsh_custom.load_into_xonsh.pkg_check", return_value=MagicMock()),
        patch(
            "kash.xonsh_custom.load_into_xonsh.check_kerm_code_support",
            return_value=False,
        ),
        patch("kash.xonsh_custom.load_into_xonsh.PrintHooks"),
        patch("kash.xonsh_custom.load_into_xonsh.cprint"),
        patch("kash.xonsh_custom.load_into_xonsh.log_command_action_info"),
    ):
        load_into_xonsh()
        assert install.called
