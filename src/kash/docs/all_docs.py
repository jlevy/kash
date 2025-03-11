from dataclasses import dataclass, field
from typing import List

from funlog import log_calls

from kash.config.logger import get_logger
from kash.docs.load_actions_info import load_action_info
from kash.docs.load_api_docs import load_api_docs
from kash.docs.load_help_topics import HelpTopics, load_help_topics
from kash.docs.load_source_code import load_source_code, SourceCode
from kash.docs_base.docs_base import DocsBase
from kash.help.help_types import CommandInfo
from kash.util.lazyobject import lazyobject


log = get_logger(__name__)


@dataclass
class AllDocs(DocsBase):
    help_topics: HelpTopics = field(default_factory=load_help_topics)
    api_docs: str = field(default_factory=load_api_docs)
    source_code: SourceCode = field(default_factory=load_source_code)
    action_infos: List[CommandInfo] = field(default_factory=load_action_info)

    def self_check(self) -> bool:
        return (
            super().self_check()
            and bool(self.api_docs.strip())
            and len(self.api_docs.splitlines()) > 5
            and self.source_code.self_check()
            and len(self.action_infos) > 5
        )

    def load(self) -> None:
        super().load()

    def __str__(self):
        return (
            "AllDocs("
            f"{len(self.help_topics.__dict__)} topic pages, "
            f"{len(self.faqs)} faqs, "
            f"{len(self.custom_command_infos)} command infos, "
            f"{len(self.std_command_infos)} std command infos, "
            f"{len(self.action_infos)} action infos, "
            f"{len(self.recipe_snippets)} snippets, "
            f"{len(self.api_docs.splitlines())} lines api docs, "
            f"{self.source_code}"
            ")"
        )


@lazyobject
@log_calls(level="info", show_return_value=False)
def all_docs() -> AllDocs:
    all_docs = AllDocs()
    if not all_docs.self_check():
        log.error("Did not load all expected docs (misconfig or are some missing?): %s", all_docs)
    log.info("Loaded docs: %s", all_docs)
    return all_docs
