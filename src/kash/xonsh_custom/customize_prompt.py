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
    workspace_str: str
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

    if ws_name and not is_global_ws:
        workspace_str = ws_name
    else:
        workspace_str = "(global_ws)"
    workspace_details = f"Workspace at {ws.base_dir}"

    cwd = Path(".").resolve()
    if cwd.is_relative_to(ws.base_dir):
        cwd_in_workspace = True
        rel_cwd = cwd.relative_to(ws.base_dir)
        if rel_cwd != Path("."):
            cwd_str = str(rel_cwd)
        else:
            cwd_str = ""
    else:
        cwd_in_workspace = False
        cwd_str = cwd.name
    cwd_details = f"Current directory at {cwd}"

    return PromptInfo(
        workspace_str, workspace_details, is_global_ws, cwd_str, cwd_details, cwd_in_workspace
    )


@dataclass(frozen=True)
class PromptSettings:
    hrule: PtkTokens
    color_bg: str
    color_normal: str
    color_warn: str
    prompt_prefix: str
    prompt_char: str
    prompt_char_color: str

    @property
    def ptk_style(self) -> str:
        return f"bold {self.color_normal} bg:{self.color_bg}"

    @property
    def ptk_style_warn(self) -> str:
        return f"bold {self.color_warn} bg:{self.color_bg}"

    @property
    def ptk_style_bg(self) -> str:
        return f"bold {self.color_bg}"


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
    inverse = "inverse"

    @property
    def settings(self) -> PromptSettings:
        """Get prompt settings for this style"""
        if self == PromptStyle.plain:
            return PromptSettings(
                hrule=ptk_newline,
                color_bg="",
                color_normal=colors.terminal.green_light,
                color_warn=colors.terminal.yellow_light,
                prompt_prefix="",
                prompt_char=PROMPT_MAIN,
                prompt_char_color=colors.terminal.green_light,
            )
        elif self == PromptStyle.clean_dark:
            return PromptSettings(
                hrule=ptk_newline,
                color_bg=colors.terminal.black_dark,
                color_normal=colors.terminal.green_light,
                color_warn=colors.terminal.yellow_light,
                prompt_prefix=" ",  # "▌" is another option
                prompt_char="",  # "\uE0B0"
                prompt_char_color=colors.terminal.black_dark,
            )
        elif self == PromptStyle.inverse:
            return PromptSettings(
                hrule=ptk_newline,
                color_bg=colors.terminal.white_dark,
                color_normal=colors.terminal.green_darker,
                color_warn=colors.terminal.yellow_darker,
                prompt_prefix=" ",
                prompt_char="",  # "\uE0B0"
                prompt_char_color=colors.terminal.white_dark,
            )
        else:
            raise AssertionError("Invalid prompt style")


def get_prompt_style() -> PromptStyle:
    """
    Get the current prompt style from `PROMPT_STYLE` environment variable or default to normal.
    """
    from kash.xonsh_custom.customize_xonsh import XSH

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

    workspace_color = settings.ptk_style_warn if info.is_global_ws else settings.ptk_style
    workspace_tokens = text_with_tooltip(
        info.workspace_str, hover_text=info.workspace_details
    ).as_ptk_tokens(style=workspace_color)

    sep = (settings.ptk_style, "/" if info.cwd_in_workspace else " ")

    if info.cwd_str:
        cwd_tokens = [sep] + text_with_tooltip(
            info.cwd_str, hover_text=info.cwd_details
        ).as_ptk_tokens(style=settings.ptk_style)
    else:
        cwd_tokens = []

    # Assemble the final prompt tokens.
    ptk_tokens = (
        settings.hrule
        + [
            (settings.ptk_style, settings.prompt_prefix),
        ]
        + workspace_tokens
        + cwd_tokens
        + [
            (settings.ptk_style, " "),  # Space before the main prompt symbol
            (
                settings.prompt_char_color,
                settings.prompt_char,
            ),  # Main prompt symbol with normal color
            ("", " "),
        ]
    )

    return FormattedText(ptk_tokens)
