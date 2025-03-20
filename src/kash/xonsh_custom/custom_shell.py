import os
import time
from collections.abc import Callable
from os.path import expanduser
from typing import cast

from prompt_toolkit.formatted_text import FormattedText
from pygments.token import Token
from strif import abbrev_str
from typing_extensions import override
from xonsh.built_ins import XSH
from xonsh.environ import xonshrc_context
from xonsh.execer import Execer
from xonsh.main import events
from xonsh.shell import Shell
from xonsh.shells.ptk_shell.formatter import PTKPromptFormatter
from xonsh.xontribs import xontribs_load

import kash.config.suppress_warnings  # noqa: F401  # usort:skip

# Keeping initial imports/deps minimal.
from kash.config import colors
from kash.config.lazy_imports import import_start_time  # usort:skip
from kash.config.logger import get_console, get_logger
from kash.config.settings import APP_NAME, find_rcfiles
from kash.config.text_styles import SPINNER
from kash.help.assistant import AssistanceType
from kash.shell.output.shell_output import cprint
from kash.shell.ui.shell_syntax import is_assist_request_str
from kash.xonsh_custom.xonsh_ranking_completer import RankingCompleter

log = get_logger(__name__)


# Whether to show Python tracebacks when there are errors.
XONSH_SHOW_TRACEBACK = True

## -- Non-customized xonsh shell setup --

xonshrc_init_script = """
# Auto-load of kash:
# This only activates if xonsh is invoked as kash.
xontrib load -f kash.xontrib.kash_extension
"""

xontrib_command = xonshrc_init_script.splitlines()[1].strip()

xonshrc_path = expanduser("~/.xonshrc")


def is_xontrib_installed(file_path):
    try:
        with open(file_path) as file:
            for line in file:
                if xontrib_command == line.strip():
                    return True
    except FileNotFoundError:
        return False
    return False


def install_to_xonshrc():
    """
    Script to add kash xontrib to the .xonshrc file.
    Not necessary if we are running our own customized shell (the default).
    """
    # Append the command to the file if not already present.
    if not is_xontrib_installed(xonshrc_path):
        with open(xonshrc_path, "a") as file:
            file.write(xonshrc_init_script)
        print(f"Updating your {xonshrc_path} to auto-run kash when xonsh is invoked as kashsh.")
    else:
        pass


## -- Custom xonsh shell setup --


class CustomPTKPromptFormatter(PTKPromptFormatter):
    """
    Adjust the prompt formatter to allow short-circuiting all the prompt parsing logic.
    We also accept a function that returns raw formatted text. This lets us support
    arbitrary ANSI codes including OSC8 links (and tooltips in Kerm).
    """

    def __init__(self, shell):
        super().__init__(shell)
        self.shell = shell

    def __call__(  # pyright: ignore
        self,
        template: Callable | str | None = None,
        **kwargs,
    ):
        if callable(template):
            try:
                result = template()
                if isinstance(result, FormattedText):
                    return result
            except Exception as e:
                log.error("Error formatting prompt: evaluating %s: %s", template, e)
                # On any error, return a simple fallback prompt.
                return FormattedText([("", "$ ")])
            # If it's not FormattedText, use it as the template for parent formatter
            template = result

        return super().__call__(template=cast(str, template), **kwargs)


# Base shell can be ReadlineShell or PromptToolkitShell.
# Completer can be RankingCompleter or the standard Completer.
# from xonsh.completer import Completer
# from xonsh.shells.readline_shell import ReadlineShell
from xonsh.shells.ptk_shell import PromptToolkitShell


class CustomAssistantShell(PromptToolkitShell):
    """
    Our custom version of the interactive xonsh shell.

    Note event hooks in xonsh don't let you disable xonsh's processing, so we use a custom shell.
    """

    def __init__(self, **kwargs):
        from xonsh.shells.ptk_shell.completer import PromptToolkitCompleter

        # Set the completer to our custom one.
        # XXX Need to disable the default Completer, then overwrite with our custom one.
        super().__init__(completer=False, **kwargs)
        self.completer = RankingCompleter()
        self.pt_completer = PromptToolkitCompleter(self.completer, self.ctx, self)

        # Use our own prompt formatter so we can control ansi codes.
        self.prompt_formatter = CustomPTKPromptFormatter(self)

        # TODO: Consider patching in additional keybindings e.g. for custom mouse support.
        # self.key_bindings = merge_key_bindings([custom_ptk_keybindings(), self.key_bindings])

        log.info(
            "CustomAssistantShell: initialized completer=%s, pt_completer=%s",
            self.completer,
            self.pt_completer,
        )

    @override
    def default(self, line, raw_line=None):
        from kash.help.assistant import shell_context_assistance

        assist_query = is_assist_request_str(line)
        if assist_query:
            try:
                with get_console().status("Thinking…", spinner=SPINNER):
                    shell_context_assistance(assist_query, assistance_type=AssistanceType.fast)
            except Exception as e:
                log.error(f"Sorry, could not get assistance: {abbrev_str(str(e), max_len=1000)}")
        else:
            # Call xonsh shell.
            super().default(line)

    # XXX Copied and overriding this method.
    @override
    def _get_prompt_tokens(self, env_name: str, prompt_name: str, **kwargs):
        env = XSH.env  # type:ignore
        assert env

        p = env.get(env_name)

        if not p and "default" in kwargs:
            return kwargs.pop("default")

        p = self.prompt_formatter(
            template=cast(Callable, p),
            threaded=env["ENABLE_ASYNC_PROMPT"],
            prompt_name=prompt_name,
        )

        # From __super__._get_prompt_tokens: Skipping this: ptk's tokenize_ansi can't
        # handle OSC8 links.
        # toks = partial_color_tokenize(p)
        # return tokenize_ansi(PygmentsTokens(toks))

        return p


# XXX xonsh's Shell class hard-codes available shell types, but does have some
# helpful scaffolding, so let's override to use ours.
class CustomShell(Shell):
    @override
    @staticmethod
    def construct_shell_cls(backend, **kwargs):
        log.info("Using %s: %s", CustomAssistantShell.__name__, kwargs)
        return CustomAssistantShell(**kwargs)


@events.on_command_not_found
def not_found(cmd: list[str]):
    from kash.help.assistant import shell_context_assistance

    # Don't call assistant on one-word typos. It's annoying.
    if len(cmd) >= 2:
        cprint("Command not found. Getting assistance…")
        with get_console().status("", spinner=SPINNER):
            shell_context_assistance(
                f"""
                The user just typed the following command, but it was not found:

                {" ".join(cmd)}

                Please give them a brief suggestion of possible correct commands
                and how they can get more help with `help` or any question
                ending with ? in the terminal.
                """,
                assistance_type=AssistanceType.fast,
            )


def customize_xonsh_settings(is_interactive: bool):
    """
    Xonsh settings to customize xonsh better kash usage.
    """
    input_color = colors.terminal.input
    default_settings = {
        # Auto-cd if a directory name is typed.
        "AUTO_CD": True,
        # Having this true makes processes hard to interrupt with Ctrl-C.
        # https://xon.sh/envvars.html#thread-subprocs
        "THREAD_SUBPROCS": False,
        "XONSH_INTERACTIVE": is_interactive,
        "XONSH_SHOW_TRACEBACK": XONSH_SHOW_TRACEBACK,
        # TODO: Consider enabling and adapting auto-suggestions.
        "AUTO_SUGGEST": False,
        # Completions can be "none", "single", "multi", or "readline".
        # "single" lets us have rich completions with descriptions alongside.
        # https://xon.sh/envvars.html#completions-display
        "COMPLETIONS_DISPLAY": "single",
        # Number of rows in the fancier prompt toolkit completion menu.
        "COMPLETIONS_MENU_ROWS": 8,
        # Mode is "default" (fills in common prefix) or "menu-complete" (fills in first match).
        "COMPLETION_MODE": "default",
        # If true, show completions always, after each keypress.
        # TODO: Find a way to do this after a delay. Instantly showing this is annoying.
        "UPDATE_COMPLETIONS_ON_KEYPRESS": False,
        # Mouse support for completions by default interferes with other mouse scrolling
        # in the terminal.
        # TODO: Enable mouse click support but disable scroll events.
        "MOUSE_SUPPORT": False,
        # Start with default colors then override prompt toolkit colors
        # being the same input color.
        "XONSH_COLOR_STYLE": "default",
        "XONSH_STYLE_OVERRIDES": {
            Token.Text: input_color,
            Token.Keyword: input_color,
            Token.Name: input_color,
            Token.Name.Builtin: input_color,
            Token.Name.Variable: input_color,
            Token.Name.Variable.Magic: input_color,
            Token.Name.Variable.Instance: input_color,
            Token.Name.Variable.Class: input_color,
            Token.Name.Variable.Global: input_color,
            Token.Name.Function: input_color,
            Token.Name.Constant: input_color,
            Token.Name.Namespace: input_color,
            Token.Name.Class: input_color,
            Token.Name.Decorator: input_color,
            Token.Name.Exception: input_color,
            Token.Name.Tag: input_color,
            Token.Keyword.Constant: input_color,
            Token.Keyword.Namespace: input_color,
            Token.Keyword.Type: input_color,
            Token.Keyword.Declaration: input_color,
            Token.Keyword.Reserved: input_color,
            Token.Punctuation: input_color,
            Token.String: input_color,
            Token.Number: input_color,
            Token.Generic: input_color,
            Token.Operator: input_color,
            Token.Operator.Word: input_color,
            Token.Other: input_color,
            Token.Literal: input_color,
            Token.Comment: input_color,
            Token.Comment.Single: input_color,
            Token.Comment.Multiline: input_color,
            Token.Comment.Special: input_color,
        },
    }

    # Apply settings, unless environment variables are already set otherwise.
    for key, default_value in default_settings.items():
        XSH.env[key] = os.environ.get(key, default_value)  # pyright: ignore


def load_rcfiles(execer: Execer, ctx: dict):
    rcfiles = [str(f) for f in find_rcfiles()]
    if rcfiles:
        log.info("Loading rcfiles: %s", rcfiles)
        xonshrc_context(rcfiles=rcfiles, execer=execer, ctx=ctx, env=XSH.env, login=True)


def start_shell(single_command: str | None = None):
    """
    Main entry point to start a customized xonsh shell, with custom shell settings.

    This does more than just the xontrib as we add hack the input loop and do some
    other customizations but then the rest of the customization is via the `kash_extension`
    xontrib.
    """
    import builtins

    # Make process title "kash" instead of "xonsh".
    try:
        from setproctitle import setproctitle

        setproctitle(APP_NAME)
    except ImportError:
        pass

    # Seems like we have to do our own setup as premain/postmain can't be customized.
    ctx = {}
    execer = Execer(
        filename="<stdin>",
        debug_level=0,
        scriptcache=True,
        cacheall=False,
    )
    XSH.load(ctx=ctx, execer=execer, inherit_env=True)
    XSH.shell = CustomShell(execer=execer, ctx=ctx)  # pyright: ignore

    # A hack to get kash help to replace Python help. We just delete the builtin help so
    # that kash's help can be used in its place (otherwise builtins override aliases).
    # Save a copy as "pyhelp".
    ctx["pyhelp"] = builtins.help
    del builtins.help
    # Same for "license" which is another easy-to-confuse builtin.
    ctx["pylicense"] = builtins.license
    del builtins.license

    is_interactive = False if single_command else True

    customize_xonsh_settings(is_interactive)

    ctx["__name__"] = "__main__"
    events.on_post_init.fire()
    events.on_pre_cmdloop.fire()

    # Load kash xontrib for rest of kash functionality.
    xontribs_load(["kash.xontrib.kash_extension"], full_module=True)

    # If we want to replicate all the xonsh settings including .xonshrc, we could call
    # start_services(). It may be problematic to support all xonsh enhancements, however,
    # so let's only load ~/.kashrc files.
    load_rcfiles(execer, ctx)

    # Imports are so slow we will need to improve this. Let's time it.
    startup_time = time.time() - import_start_time
    log.info(f"kash startup took {startup_time:.2f}s.")

    # Main loop.
    try:
        if single_command:
            # Run a command.
            XSH.shell.shell.default(single_command)  # pyright: ignore
        else:
            XSH.shell.shell.cmdloop()  # pyright: ignore
    finally:
        XSH.unload()
        XSH.shell = None
