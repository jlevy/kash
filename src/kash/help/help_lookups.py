import inspect
from collections.abc import Callable
from pathlib import Path

from thefuzz import fuzz

from kash.docs.all_docs import all_docs
from kash.exec.command_registry import CommandFunction
from kash.help.help_types import Faq
from kash.model.actions_model import Action
from kash.utils.errors import FileNotFound, NoMatch


def look_up_source_code(command_or_action: CommandFunction | Action | type[Action]) -> Path:
    """
    Get the path to the source code for a command or action.
    """
    # Action classes and instances should have a __source_path__ attribute, because
    # the original source may have been wrapped within another source file.
    source_path = getattr(command_or_action, "__source_path__", None)
    if not source_path and isinstance(command_or_action, Callable):
        # Commands are just the original function with a decorator in the same source file,
        # so inspect should be accurate.
        source_path = inspect.getsourcefile(command_or_action)
    if not source_path:
        raise FileNotFound(f"No source path found for command or action: {command_or_action}")

    resolved_path = Path(source_path).resolve()
    if not resolved_path.exists():
        raise FileNotFound(
            f"File not found for command or action {command_or_action}: {resolved_path}"
        )

    return resolved_path


def look_up_faq(text: str) -> Faq:
    """
    Look up a FAQ by question. Requires nearly an exact match. For approximate
    matching use embeddings.
    """

    def faq_match(text: str, faq: Faq) -> bool:
        def normalize(s: str) -> str:
            return s.strip(" ?").lower()

        normalized_text = normalize(text)
        normalized_question = normalize(faq.question)
        ratio = fuzz.ratio(normalized_text, normalized_question)

        if len(normalized_text) <= 10:
            return ratio >= 98
        else:
            return ratio >= 95

    for faq in all_docs.faqs:
        if faq_match(text, faq):
            return faq

    raise NoMatch()
