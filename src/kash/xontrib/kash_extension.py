"""
Xonsh extension for kash.

These are the additions to xonsh that don't involve customizing the shell itself.

Sets up all commands and actions for use in xonsh.

Can run from the custom kash shell (main.py) or from a regular xonsh shell.
"""

# Using absolute imports to avoid polluting the user's shell namespace.
import kash.actions
import kash.exec.command_registry
import kash.shell.output.shell_output
import kash.utils.common.format_utils
import kash.xonsh_custom.load_into_xonsh
import kash.xonsh_custom.shell_load_commands
import kash.xonsh_custom.xonsh_env
from kash.config.logger import get_logger
from kash.exec.action_registry import reload_all_action_classes


# We add action loading here directly in the xontrib so we expose `load` and
# can update the aliases.
@kash.exec.command_registry.kash_command
def load(*paths: str) -> None:
    """
    Load kash Python extensions. Simply imports and the defined actions should use
    @kash_action to register themselves.
    """
    import importlib
    import os
    import runpy

    from prettyfmt import fmt_path

    for path in paths:
        if os.path.isfile(path) and path.endswith(".py"):
            runpy.run_path(path, run_name="__main__")
        else:
            importlib.import_module(path)

    # Now reload all actions into the environment so the new action is visible.
    actions = reload_all_action_classes()
    kash.xonsh_custom.shell_load_commands._register_actions_in_shell(actions)

    kash.shell.output.shell_output.cprint(
        "Imported extensions and reloaded actions: %s",
        ", ".join(fmt_path(p) for p in paths),
    )
    # TODO: Track and expose to the user which extensions are loaded.


kash.xonsh_custom.xonsh_env.set_alias("load", load)

try:
    kash.xonsh_custom.load_into_xonsh.load_into_xonsh()
except Exception as e:
    log = get_logger(__name__)
    log.error("Could not initialize kash: %s", e)
    raise
