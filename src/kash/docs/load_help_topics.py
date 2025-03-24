from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

from kash.config.logger import get_logger

log = get_logger(__name__)


def load_help_src(path: str) -> str:
    if not path.endswith(".md"):
        path += ".md"
    base_dir = Path(__file__).parent
    topic_file = base_dir / path
    if not topic_file.exists():
        raise ValueError(f"Unknown doc: {topic_file}")

    return topic_file.read_text()


def page_field(path: str):
    return field(default_factory=lambda: load_help_src(path))


@dataclass(frozen=True)
class HelpTopics:
    welcome: str = page_field("markdown/welcome")
    warning: str = page_field("markdown/warning")
    what_is_kash: str = page_field("markdown/topics/a1_what_is_kash")
    installation: str = page_field("markdown/topics/a2_installation")
    getting_started: str = page_field("markdown/topics/a3_getting_started")
    elements: str = page_field("markdown/topics/a4_elements")
    tips_for_use_with_other_tools: str = page_field(
        "markdown/topics/a5_tips_for_use_with_other_tools"
    )
    philosophy_of_kash: str = page_field("markdown/topics/b0_philosophy_of_kash")
    kash_overview: str = page_field("markdown/topics/b1_kash_overview")
    workspace_and_file_formats: str = page_field("markdown/topics/b2_workspace_and_file_formats")
    modern_shell_tool_recommendations: str = page_field(
        "markdown/topics/b3_modern_shell_tool_recommendations"
    )
    faq: str = page_field("markdown/topics/b4_faq")


@cache
def load_help_topics() -> HelpTopics:
    return HelpTopics()
