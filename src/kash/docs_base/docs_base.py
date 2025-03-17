from dataclasses import dataclass, field
from functools import cached_property

from funlog import log_calls

from kash.config.logger import get_logger
from kash.docs_base.load_custom_command_info import load_custom_command_info
from kash.docs_base.load_faqs import load_faqs
from kash.docs_base.load_recipe_snippets import load_recipe_snippets
from kash.help.help_embeddings import HelpIndex
from kash.help.help_types import CommandInfo, Faq, RecipeSnippet
from kash.help.tldr_help import tldr_descriptions
from kash.utils.common.lazyobject import lazyobject
from kash.xonsh_custom.shell_which import is_valid_command

log = get_logger(__name__)


@dataclass
class DocsBase:
    """
    Class to hold basic shell docs. Leaving non-frozen so we can subclass easily
    to add more custom docs.
    """

    faqs: list[Faq] = field(default_factory=load_faqs)
    custom_command_infos: list[CommandInfo] = field(default_factory=load_custom_command_info)
    std_command_infos: list[CommandInfo] = field(default_factory=tldr_descriptions)
    recipe_snippets: list[RecipeSnippet] = field(default_factory=load_recipe_snippets)

    # TODO: Consider a TTLCache for this in case we add/remove commands.
    @cached_property
    def usable_snippets(self) -> list[RecipeSnippet]:
        snippets = self.recipe_snippets

        def commands_in_path(snippet: RecipeSnippet) -> bool:
            return all(is_valid_command(cmd) for cmd in snippet.command.uses)

        usable_snippets = [s for s in snippets if commands_in_path(s)]
        log.info(
            "Checked for recipe snippets in path: %s/%s usable",
            len(usable_snippets),
            len(snippets),
        )
        return usable_snippets

    @cached_property
    def help_index(self) -> HelpIndex:
        """
        Get command and action info, code snippets, and FAQs as queryable embeddings.
        """
        return HelpIndex(list(self.faqs + self.custom_command_infos + self.recipe_snippets))

    def self_check(self) -> bool:
        # Sanity check that we loaded all expected docs.
        return (
            len(self.faqs) > 5 and len(self.std_command_infos) > 5 and len(self.recipe_snippets) > 5
        )

    def load(self) -> None:
        help_index = self.help_index
        log.message("Loaded help index: %d items", len(help_index))

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return (
            "DocsBase("
            f"{len(self.faqs)} faqs, "
            f"{len(self.custom_command_infos)} command infos, "
            f"{len(self.std_command_infos)} std command infos, "
            f"{len(self.recipe_snippets)} snippets, "
            ")"
        )


@lazyobject
@log_calls(level="info", show_return_value=False)
def docs_base() -> DocsBase:
    docs_base = DocsBase()
    if not docs_base.self_check():
        log.error("Did not load all expected docs (misconfig or are some missing?): %s", docs_base)
    log.info("Loaded docs: %s", docs_base)
    return docs_base
