from kash.config.setup import setup
from kash.config.text_styles import LOGO_NAME, STYLE_HINT
from kash.xonsh_custom.shell_load_commands import (
    is_interactive,
    log_command_action_info,
    reload_shell_commands_and_actions,
    set_env,
)

setup(rich_logging=True)  # Set up logging first.

import time

from xonsh.built_ins import XSH
from xonsh.prompt.base import PromptFields

from kash.commands.base.general_commands import self_check
from kash.commands.help import doc_commands
from kash.config.logger import get_logger
from kash.config.settings import check_kerm_code_support
from kash.local_server.local_server import start_local_server
from kash.local_server.local_url_formatters import enable_local_urls
from kash.shell.output.shell_output import PrintHooks, cprint
from kash.shell.utils.native_utils import sys_tool_check
from kash.shell.version import get_version_tag
from kash.workspaces import current_ws
from kash.xonsh_custom.customize_prompt import get_prompt_info, kash_xonsh_prompt
from kash.xonsh_custom.xonsh_completers import load_completers
from kash.xonsh_custom.xonsh_modern_tools import modernize_shell

log = get_logger(__name__)


def _kash_workspace_str() -> str:
    return get_prompt_info().workspace_name


def _shell_interactive_setup():
    from kash.xonsh_custom.xonsh_completers import add_key_bindings

    # Set up a prompt field for the workspace string.
    fields = PromptFields(XSH)
    fields["workspace_str"] = _kash_workspace_str
    set_env("PROMPT_FIELDS", fields)

    # Set up the prompt and title template.
    set_env("PROMPT", kash_xonsh_prompt)
    set_env("TITLE", LOGO_NAME + " - {workspace_str}")

    add_key_bindings()

    modernize_shell()


def load_into_xonsh():
    """
    Everything to load kash setup and commands in xonsh from within xonsh, as a xontrib.
    """

    if is_interactive():
        # Do first so in case there is an error, the shell prompt etc works as expected.
        _shell_interactive_setup()

        # Then do welcome first since init could take a few seconds.
        doc_commands.welcome()

        def load():
            load_start_time = time.time()

            reload_shell_commands_and_actions()

            load_time = time.time() - load_start_time
            log.info(f"Action and command loading took {load_time:.2f}s.")

            # Completers depend on commands and actions being loaded.
            load_completers()

            # TODO: Consider preloading but handle failure?
            # all_docs.load()

        load()
        # Another idea was to try to seem a little faster starting up when interactive
        # but doesn't seem worth it.
        # load_thread = threading.Thread(target=load)
        # load_thread.start()

        PrintHooks.after_interactive()

        self_check(brief=True)

        # Currently only Kerm supports our advanced UI with Kerm codes.
        supports_kerm_codes = check_kerm_code_support()
        if supports_kerm_codes:
            start_local_server()
            enable_local_urls(True)
        else:
            cprint(
                "If your terminal supports it, you may use `start_local_server` to enable local links.",
                style=STYLE_HINT,
            )

        cprint()
        log_command_action_info()

        current_ws()  # Validates and logs info for user.

        sys_tool_check().warn_if_missing()

    else:
        reload_shell_commands_and_actions()

    log.info("kash %s loaded", get_version_tag())
