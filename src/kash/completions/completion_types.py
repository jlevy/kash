from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, NewType, Optional, TypeAlias

from prettyfmt import abbrev_obj
from strif import abbrev_str
from xonsh.completers.tools import RichCompletion

from kash.config.logger import get_logger
from kash.help.help_types import HelpDoc

log = get_logger(__name__)


Score = NewType("Score", float)
"""As with thefuzz scoring, a score is a float between 0 and 100."""

COMPLETION_DISPLAY_MAX_LEN = 60
COMPLETION_DESCRIPTION_MAX_LEN = 80


class CompletionGroup(int, Enum):
    """
    Groupings of completions, sorted from most to least important.
    """

    top_suggestion = 0
    kash = 1
    help = 2
    relevant_options = 3
    recommanded_shell_command = 4
    recognized_shell_command = 5
    python = 6
    unknown = 9


@dataclass(frozen=True)
class CompletionValue:
    """
    An immutable completion value, useful for caching etc.
    """

    group: CompletionGroup
    value: str
    display: Optional[str]
    help_doc: Optional[HelpDoc] = None
    description: str = ""
    style: str = ""
    append_space: bool = False
    replace_input: bool = False


class ScoredCompletion(RichCompletion):
    """
    Subclass of RichCompletion that adds a score and display priority.
    """

    def __init__(
        self,
        value: str,
        group: CompletionGroup = CompletionGroup.unknown,
        help_doc: Optional[HelpDoc] = None,
        score: Optional[Score] = None,
        replace_input: bool = False,
        prefix_len: Optional[int] = None,
        display: Optional[str] = None,
        description: str = "",
        style: str = "",
        append_closing_quote: bool = True,
        append_space: bool = False,
    ):
        super().__init__(
            value, prefix_len, display, description, style, append_closing_quote, append_space
        )
        self.score = score
        self.group = group
        self.help_doc = help_doc
        self.replace_input = replace_input

    @classmethod
    def from_unscored(cls, completion: RichCompletion | str) -> ScoredCompletion:
        if isinstance(completion, RichCompletion):
            return cls(completion, **completion.__dict__)
        else:
            return cls(completion)

    @classmethod
    def from_value(cls, value: CompletionValue):
        return cls(
            value=value.value,
            group=value.group,
            help_doc=value.help_doc,
            display=(
                abbrev_str(value.display, COMPLETION_DISPLAY_MAX_LEN)
                if value.display
                else abbrev_str(value.value, COMPLETION_DISPLAY_MAX_LEN)
            ),
            description=abbrev_str(value.description, COMPLETION_DESCRIPTION_MAX_LEN),
            style=value.style,
            append_space=value.append_space,
            replace_input=value.replace_input,
        )

    @classmethod
    def from_help_doc(cls, help_doc: HelpDoc):
        return cls.from_value(help_doc.completion_value())

    def replace(self, **kwargs: Dict[str, Any]) -> ScoredCompletion:
        default_kwargs: Dict[str, Any] = dict(
            value=self.value,
            **self.__dict__,
        )
        default_kwargs.update(kwargs)
        return ScoredCompletion(**default_kwargs)

    def formatted(self) -> str:
        s = f"Group{self.group.value} {self.score or float('-inf'):2.1f} {self.value!r}"
        if self.display:
            s += f" ({self.display!r} {self.style!r})"
        if self.replace_input:
            s += f" (replace_input {self.replace_input}"
        if self.prefix_len:
            s += f" (prefix_len {self.prefix_len})"
        if self.description:
            s += f" - {abbrev_str(self.description, 25)}"
        return s

    def __repr__(self):
        return abbrev_obj(self)


@dataclass(frozen=True, order=True)
class SortKey:
    """
    Sort first by explicit priority, then by score (value should be negative, and
    unscored will sort last), then prefix matches, then by value.
    """

    group: CompletionGroup
    neg_score: Optional[Score]
    value: str

    def __post_init__(self):
        if not self.neg_score:
            object.__setattr__(self, "neg_score", Score(float("inf")))


SortKeyFn: TypeAlias = Callable[[ScoredCompletion], SortKey]
"""
A completion sorting function.
"""
