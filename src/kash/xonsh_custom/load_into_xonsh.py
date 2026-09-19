from kash.config.setup import kash_setup

kash_setup(rich_logging=True)  # Set up logging first.

import time

from clideps.pkgs.pkg_check import pkg_check
from xonsh.built_ins import XSH
from xonsh.prompt.base import PromptFields

from kash.commands.base.general_commands import self_check
from kash.commands.help.welcome import welcome
from kash.config.logger import get_logger
from kash.config.settings import RECOMMENDED_PKGS, check_kerm_code_support
from kash.config.text_styles import STYLE_HINT
from kash.mcp.mcp_server_commands import start_mcp_server
from kash.shell.output.shell_output import PrintHooks, cprint
from kash.workspaces import current_ws
from kash.xonsh_custom.customize_prompt import get_prompt_info, kash_xonsh_prompt, kash_xonsh_title
from kash.xonsh_custom.shell_load_commands import (
    is_interactive,
    log_command_action_info,
    reload_shell_commands_and_actions,
    set_env,
)
from kash.xonsh_custom.xonsh_completers import load_completers
from kash.xonsh_custom.xonsh_keybindings import add_key_bindings
from kash.xonsh_custom.xonsh_modern_tools import modernize_shell

log = get_logger(__name__)


def recover_from_init_failure(exc: Exception) -> None:
    """
    Keep the shell usable after a failed xontrib init.

    Xonsh treats a raised xontrib exception as a failed load and then renders
    its default prompt template unsubstituted.
    """
    log.error("Could not initialize kash: %s", exc, exc_info=exc)
    try:
        _install_prompt()
    except Exception as prompt_error:
        log.error("Could not install fallback prompt: %s", prompt_error)


def _install_prompt() -> None:
    """
    Install the kash prompt first so later init failures cannot leave xonsh
    rendering an unsubstituted default template.
    """
    set_env("PROMPT", kash_xonsh_prompt)
    set_env("TITLE", kash_xonsh_title)


def _shell_interactive_setup():
    _install_prompt()

    try:
        fields = PromptFields(XSH)
        prompt_info = get_prompt_info()
        fields["workspace_str"] = prompt_info.workspace_name
        fields["cwd_short_str"] = prompt_info.cwd_short_str
        set_env("PROMPT_FIELDS", fields)
    except Exception as e:
        log.warning("Could not initialize prompt fields: %s", e)

    try:
        add_key_bindings()
    except Exception as e:
        log.warning("Could not add key bindings: %s", e)

    try:
        modernize_shell()
    except Exception as e:
        log.warning("Could not modernize shell: %s", e)


def load_into_xonsh():
    """
    Everything to load kash setup and commands in xonsh from within xonsh, as a xontrib.
    """

    if is_interactive():
        # Prompt first so any later exception still leaves a usable shell.
        try:
            _install_prompt()
        except Exception as e:
            log.warning("Could not install kash prompt: %s", e)

        try:
            welcome()
        except Exception as e:
            log.warning("Could not show welcome: %s", e)

        try:
            _shell_interactive_setup()
        except Exception as e:
            log.warning("Could not complete interactive setup: %s", e)
            try:
                _install_prompt()
            except Exception:
                pass

        try:
            load_start_time = time.time()
            reload_shell_commands_and_actions()
            load_time = time.time() - load_start_time
            log.info(f"Action and command loading took {load_time:.2f}s.")
            load_completers()
        except Exception as e:
            log.error("Could not load commands and actions: %s", e, exc_info=True)

        try:
            PrintHooks.after_interactive()
        except Exception as e:
            log.debug("after_interactive hook failed: %s", e)

        try:
            self_check(brief=True)
        except Exception as e:
            log.warning("self_check failed: %s", e)

        try:
            # Currently only Kerm supports our advanced UI with Kerm codes.
            supports_kerm_codes = check_kerm_code_support()
            if supports_kerm_codes:
                # Don't pay for import until needed.
                from kash.local_server.local_server import start_ui_server
                from kash.local_server.local_url_formatters import enable_local_urls

                start_ui_server()
                enable_local_urls(True)
            else:
                cprint(
                    "If your terminal supports it, you may use `start_ui_server` to enable local links.",
                    style=STYLE_HINT,
                )
        except Exception as e:
            log.warning("Could not start UI server: %s", e)

        try:
            start_mcp_server()
        except Exception as e:
            log.warning("Could not start MCP server: %s", e)

        try:
            cprint()
            log_command_action_info()
        except Exception as e:
            log.debug("Could not log command info: %s", e)

        try:
            current_ws()  # Validates and logs info for user.
        except Exception as e:
            log.warning("Could not load workspace: %s", e)

        try:
            pkg_check().warn_if_missing(*RECOMMENDED_PKGS)
        except Exception as e:
            log.debug("Package check failed: %s", e)

    else:
        try:
            reload_shell_commands_and_actions()
        except Exception as e:
            log.error("Could not load commands and actions: %s", e, exc_info=True)
