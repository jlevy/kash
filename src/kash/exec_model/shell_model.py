from typing import Any, Optional

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

from kash.exec_model.commands_model import Command


@dataclass(frozen=True, config=ConfigDict(arbitrary_types_allowed=True))
class ShellResult:
    """
    Everything needed to handle and display the result of an action or command
    in the shell.
    """

    result: Optional[Any] = None
    show_result: bool = False
    show_selection: bool = False
    suggest_actions: bool = False
    display_command: Optional[Command] = None
    exception: Optional[Exception] = None
