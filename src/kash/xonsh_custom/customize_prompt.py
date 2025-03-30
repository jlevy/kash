from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from prompt_toolkit.formatted_text import FormattedText

from kash.config import colors
from kash.config.logger import get_console
from kash.config.text_styles import PROMPT_MAIN
from kash.shell.output.kerm_code_utils import text_with_tooltip
from kash.workspaces import current_ws

# Xonsh default prompt for reference:
# dp = (
#     "{YELLOW}{env_name}{RESET}"
#     "{BOLD_GREEN}{user}@{hostname}{BOLD_BLUE} "
#     "{cwd}{branch_color}{curr_branch: {}}{RESET} "
#     "{RED}{last_return_code_if_nonzero:[{BOLD_INTENSE_RED}{}{RED}] }{RESET}"
#     "{BOLD_BLUE}{prompt_end}{RESET} "
# )

PtkToken = tuple[str, str]
PtkTokens = list[PtkToken]


@dataclass(frozen=True)
class PromptInfo:
    workspace_name: str
    workspace_details: str
    is_global_ws: bool
    cwd_str: str
    cwd_details: str
    cwd_in_workspace: bool


def get_prompt_info() -> PromptInfo:
    # Could do this faster with current_workspace_info() but actually it's nicer to load
    # and log info about the whole workspace after a cd so we do that.
    ws = current_ws()
    ws_name = ws.name
    is_global_ws = ws.is_global_ws
    workspace_details = f"Workspace at {ws.base_dir}"

    cwd = Path(".").resolve()
    if cwd.is_relative_to(ws.base_dir):
        cwd_in_workspace = True
        rel_cwd = cwd.relative_to(ws.base_dir)
        if rel_cwd != Path("."):
            cwd_str = str(rel_cwd)
        else:
            cwd_str = ""
    elif cwd.is_relative_to(Path.home()):
        cwd_in_workspace = False
        rel_to_home = cwd.relative_to(Path.home())
        if rel_to_home != Path("."):
            cwd_str = "~/" + rel_to_home.as_posix()
        else:
            cwd_str = "~"
    else:
        cwd_in_workspace = False
        cwd_str = cwd.as_posix()

    cwd_details = f"Current directory at {cwd}"

    return PromptInfo(
        ws_name, workspace_details, is_global_ws, cwd_str, cwd_details, cwd_in_workspace
    )


@dataclass(frozen=True)
class PromptSettings:
    hrule: PtkTokens
    color_bg: str
    color_normal: str
    color_bright: str
    color_dim: str
    prompt_prefix: str
    prompt_char: str
    prompt_char_color: str

    @property
    def ptk_style_normal(self) -> str:
        return f"bold {self.color_normal} bg:{self.color_bg}"

    @property
    def ptk_style_bright(self) -> str:
        return f"bold {self.color_bright} bg:{self.color_bg}"

    @property
    def ptk_style_dim(self) -> str:
        return f"bold {self.color_dim} bg:{self.color_bg}"

    @property
    def ptk_style_bg(self) -> str:
        return f"{self.color_bg}"


ptk_newline: PtkTokens = [("", "\n")]

# Could cap at CONSOLE_WRAP_WIDTH if desired, but this is prettier on wide terminals.
hrule_width = get_console().width

# Kind of looks nice but ugly with copy/paste.
ptk_hrule: PtkTokens = [(colors.terminal.black_dark, "─" * hrule_width), ("", "\n")]


class PromptStyle(Enum):
    """
    Not offering tons of customization here, but just a couple good fixed options.
    """

    default = clean_dark = "clean_dark"
    plain = "plain"

    @property
    def settings(self) -> PromptSettings:
        """Get prompt settings for this style"""
        if self == PromptStyle.plain:
            return PromptSettings(
                hrule=ptk_newline,
                color_bg="",
                color_normal=colors.terminal.green_light,
                color_bright=colors.terminal.yellow_light,
                color_dim=colors.terminal.black_light,
                prompt_prefix="▌",
                prompt_char=PROMPT_MAIN,
                prompt_char_color=colors.terminal.green_light,
            )
        elif self == PromptStyle.clean_dark:
            return PromptSettings(
                hrule=ptk_newline,
                color_bg=colors.terminal.black_dark,
                color_normal=colors.terminal.green_light,
                color_bright=colors.terminal.yellow_light,
                color_dim=colors.terminal.black_light,
                prompt_prefix="▌",
                prompt_char="",  # "\uE0B0"
                prompt_char_color=colors.terminal.black_dark,
            )
        else:
            raise AssertionError("Invalid prompt style")


def get_prompt_style() -> PromptStyle:
    """
    Get the current prompt style from `PROMPT_STYLE` environment variable or default to normal.
    """
    from kash.xonsh_custom.load_into_xonsh import XSH

    assert XSH.env
    style_name = str(XSH.env.get("PROMPT_STYLE", PromptStyle.default.value)).lower()
    try:
        return PromptStyle(style_name)
    except ValueError:
        return PromptStyle.plain


def kash_xonsh_prompt() -> FormattedText:
    # Prepare the workspace string with appropriate coloring

    settings = get_prompt_style().settings
    info = get_prompt_info()

    workspace_color = settings.ptk_style_bright
    workspace_tokens = text_with_tooltip(
        info.workspace_name, hover_text=info.workspace_details
    ).as_ptk_tokens(style=workspace_color)

    cwd_style = settings.ptk_style_bright if info.cwd_in_workspace else settings.ptk_style_normal
    # Use two-line prompt if cwd is outside workspace, one-line prompt otherwise.
    if info.cwd_str and not info.cwd_in_workspace:
        cwd_tokens = (
            [(settings.ptk_style_dim, "\n" + settings.prompt_prefix)]
            + text_with_tooltip(info.cwd_str, hover_text=info.cwd_details).as_ptk_tokens(
                style=cwd_style
            )
            + [(settings.ptk_style_dim, " ")]
        )
    elif info.cwd_str:
        cwd_tokens = text_with_tooltip(info.cwd_str, hover_text=info.cwd_details).as_ptk_tokens(
            style=cwd_style
        )
    else:
        cwd_tokens = []

    # Assemble the final prompt tokens.
    ptk_tokens = (
        settings.hrule
        + [(settings.ptk_style_dim, settings.prompt_prefix)]
        + [
            (settings.ptk_style_dim, "workspace: "),
        ]
        + workspace_tokens
        + [
            (settings.ptk_style_dim, " "),
        ]
        + cwd_tokens
        + [
            (
                settings.prompt_char_color,
                settings.prompt_char,
            ),  # Main prompt symbol with normal color
            ("", " "),
        ]
    )

    return FormattedText(ptk_tokens)
