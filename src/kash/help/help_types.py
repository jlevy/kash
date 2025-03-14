from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from pydantic import BaseModel
from rich.console import Group
from rich.text import Text
from strif import abbrev_str, single_line

from kash.config.text_styles import (
    COLOR_HINT,
    EMOJI_ACTION,
    EMOJI_COMMAND,
    EMOJI_HELP,
    EMOJI_RECOMMENDED,
    EMOJI_SHELL,
    EMOJI_SNIPPET,
    STYLE_HELP_QUESTION,
    STYLE_KASH_COMMAND,
)
from kash.exec_model.commands_model import CommentedCommand
from kash.exec_model.script_model import Script
from kash.help.recommended_commands import STANDARD_SHELL_COMMANDS
from kash.shell_output.kmarkdown import KMarkdown
from kash.shell_ui.shell_syntax import assist_request_str

if TYPE_CHECKING:
    from kash.completions.completion_types import CompletionValue


class HelpDocType(Enum):
    faq = "faq"
    command_info = "command_info"
    recipe_snippet = "recipe_snippet"


class CommandType(Enum):
    shell_recommended = "shell_recommended"
    shell_other = "shell_other"
    kash_command = "kash_command"
    kash_action = "kash_action"

    @property
    def emoji(self) -> str:
        return {
            CommandType.shell_recommended: EMOJI_RECOMMENDED,
            CommandType.shell_other: EMOJI_SHELL,
            CommandType.kash_command: EMOJI_COMMAND,
            CommandType.kash_action: EMOJI_ACTION,
        }[self]

    @property
    def style(self) -> str:
        return {
            CommandType.shell_recommended: "",
            CommandType.shell_other: "",
            CommandType.kash_command: STYLE_KASH_COMMAND,
            CommandType.kash_action: STYLE_KASH_COMMAND,
        }[self]


class HelpDoc(BaseModel, ABC):
    """
    Base class for help doc types.
    """

    doc_type: HelpDocType

    @abstractmethod
    def emoji(self) -> str:
        pass

    @abstractmethod
    def embedding_text(self) -> str:
        pass

    @abstractmethod
    def completion_value(self) -> CompletionValue:
        pass

    @abstractmethod
    def __rich__(self) -> Text:
        pass


class Faq(HelpDoc):
    doc_type: HelpDocType = HelpDocType.faq
    question: str
    answer: str

    def emoji(self) -> str:
        return EMOJI_HELP

    def embedding_text(self) -> str:
        return f"{self.question}\n{self.answer}"

    def completion_value(self) -> CompletionValue:
        from kash.completions.completion_types import CompletionGroup, CompletionValue

        return CompletionValue(
            group=CompletionGroup.help,
            help_doc=self,
            value=assist_request_str(self.question),
            display=f"{self.emoji()} {self.question.lstrip('? ')}",
            style=STYLE_HELP_QUESTION,
            replace_input=True,  # FAQs should replace the entire input.
            append_space=True,
        )

    def __str__(self) -> str:
        return f"{self.emoji()} {self.question}: {abbrev_str(single_line(self.answer), max_len=40)}"

    def __rich__(self) -> Group:
        return Group(Text(self.question, style="bold"), "\n", KMarkdown(self.answer))


class CommandInfo(HelpDoc):
    """
    Information about a kash command or action or a shell command.
    """

    doc_type: HelpDocType = HelpDocType.command_info
    command_type: CommandType

    command: str

    description: str
    """Short description or docstring for the command."""

    help_page: str | None
    """Full help page, including description and any other docs."""

    def emoji(self) -> str:
        return self.command_type.emoji

    def embedding_text(self) -> str:
        return f"{self.command}\n{self.help_page}"

    def completion_value(self) -> CompletionValue:
        from kash.completions.completion_types import CompletionGroup, CompletionValue

        # Map this command info to completion groups based on whether it's
        # a kash command or action, recommended shell command, etc.
        if self.command_type == CommandType.kash_command:
            group = CompletionGroup.kash
        elif self.command_type == CommandType.kash_action:
            group = CompletionGroup.kash
        elif self.command.strip() in STANDARD_SHELL_COMMANDS:
            group = CompletionGroup.recommanded_shell_command
        elif self.description:
            group = CompletionGroup.recognized_shell_command
        else:
            group = CompletionGroup.unknown

        return CompletionValue(
            group=group,
            help_doc=self,
            value=self.command,
            display=f"{self.emoji()} {self.command}  ",
            description=single_line(self.description),
            style=self.command_type.style,
            replace_input=True,
            append_space=True,
        )

    def __str__(self) -> str:
        return f" {self.emoji()} {self.command}: {abbrev_str(single_line(self.description), max_len=40)}"

    def __rich__(self) -> Text:
        return Text.assemble(
            Text(self.command, style="bold"),
            "\n",
            Text(self.description),
        )


class RecipeSnippet(HelpDoc):
    doc_type: HelpDocType = HelpDocType.recipe_snippet
    command: CommentedCommand

    def emoji(self) -> str:
        return EMOJI_SNIPPET

    def embedding_text(self) -> str:
        return self.command.script_str

    def completion_value(self) -> CompletionValue:
        from kash.completions.completion_types import CompletionGroup, CompletionValue

        return CompletionValue(
            group=CompletionGroup.recommanded_shell_command,
            help_doc=self,
            value=self.command.command_line,
            display=f"{self.emoji()} {self.command.command_line}",
            description=f"{self.command.comment}" if self.command.comment else "",
            style="",
            replace_input=True,
            append_space=True,
        )

    def __str__(self) -> str:
        return f"{self.emoji()} {self.command.script_str}"

    def __rich__(self) -> Text:
        if self.command.comment:
            return Text.assemble(
                Text(f"# {self.command.comment}", style=COLOR_HINT),
                "\n",
                Text(self.command.command_line),
            )
        else:
            return Text(self.command.command_line)


@dataclass(frozen=True)
class RecipeScript:
    """
    A script where each command can be considered a snippet, possibly with
    a comment.
    """

    name: str
    script: Script

    def all_snippets(self) -> list[CommentedCommand]:
        """Return all commands that have a comment explaining what they do."""
        return [c for c in self.script.commands if isinstance(c, CommentedCommand) and c.comment]
