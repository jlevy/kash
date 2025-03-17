from __future__ import annotations

import re
from textwrap import dedent

from pydantic import BaseModel

from kash.exec_model.args_model import Signature
from kash.exec_model.commands_model import CommentedCommand, as_comment
from kash.utils.common.parse_shell_args import shell_split


class BareComment(BaseModel):
    """
    A comment that is not associated with a command.
    """

    text: str

    @property
    def script_str(self) -> str:
        return as_comment(self.text)


class Script(BaseModel):
    """
    A script of commands to be executed. Also useful for lists of
    commented commands, such as for kash example docs.
    """

    signature: Signature | None
    """
    The signature of the script, which is the signature of the first command.
    """

    commands: list[BareComment | CommentedCommand]
    """
    Comments or commands to be executed.
    """

    def formatted_signature(self) -> str | None:
        if not self.signature:
            return None
        else:
            return f"# Signature: {self.signature.human_str()}"

    @property
    def script_str(self) -> str:
        return "\n\n".join(
            filter(
                None,
                [
                    self.formatted_signature(),
                    *[cmd.script_str for cmd in self.commands],
                ],
            )
        )

    @classmethod
    def parse(cls, text: str) -> Script:
        """
        Parse a script from text, breaking it into paragraphs and converting each into
        either a BareComment or CommentedCommand. Handles line continuations with backslash.
        """
        # Split into paragraphs (2+ newlines).
        paragraphs = re.split(r"\n{2,}", text.strip())
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        commands = []

        for para in paragraphs:
            # Split paragraph into lines and handle line continuations
            lines = para.split("\n")
            current_comment = None  # For accumulating comment lines
            current_command = []  # For accumulating command lines

            i = 0
            while i < len(lines):
                line = lines[i].rstrip()
                stripped_line = line.strip()

                if stripped_line.startswith("#"):
                    # Line is a comment.
                    comment_line = stripped_line.lstrip("#").strip()
                    if current_comment:
                        current_comment += "\n" + comment_line
                    else:
                        current_comment = comment_line
                elif stripped_line:
                    # Line is a command. Handle line continuation.
                    while line.endswith("\\"):
                        current_command.append(line[:-1])  # Remove the backslash
                        i += 1
                        if i < len(lines):
                            line = lines[i].rstrip()
                        else:
                            break

                    # Add the last line (without backslash).
                    current_command.append(line)

                    # Process the complete command
                    full_command = "\n".join(current_command)
                    command_name = shell_split(full_command)[0]
                    commands.append(
                        CommentedCommand(
                            comment=current_comment,
                            command_line=full_command,
                            uses=[command_name],
                        )
                    )
                    current_comment = None
                    current_command = []

                i += 1

            # If there's a comment with no command following it.
            if current_comment:
                commands.append(BareComment(text=current_comment))
                current_comment = None

        return cls(signature=None, commands=commands)


## Tests


def test_script_parse_comments_and_continuations():
    # Test input with bare comments and line continuations
    test_input = dedent(
        r"""
        # This is a standalone comment
        # that spans multiple lines.

        echo hello

        # This comment belongs to the command.
        echo hello \
            world \
            with continuation

        # Another bare comment.
        """
    )

    script = Script.parse(test_input)

    print(script.script_str)

    assert script.script_str == test_input.strip()

    assert len(script.commands) == 4

    # Check first bare comment
    assert isinstance(script.commands[0], BareComment)
    assert script.commands[0].text == "This is a standalone comment\nthat spans multiple lines."

    # Check command with continuation
    assert isinstance(script.commands[2], CommentedCommand)
    assert script.commands[2].comment == "This comment belongs to the command."
    assert script.commands[2].command_line == "echo hello \n    world \n    with continuation"
    assert script.commands[2].uses == ["echo"]
