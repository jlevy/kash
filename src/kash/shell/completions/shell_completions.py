import sys
from pathlib import Path
from typing import Any

from funlog import tally_calls
from prettyfmt import fmt_lines
from strif import abbrev_str, single_line
from typing_extensions import TypeVar

from kash.commands.help.help_commands import HELP_COMMANDS
from kash.config.logger import get_logger
from kash.config.text_styles import EMOJI_COMMAND, STYLE_KASH_COMMAND
from kash.docs.all_docs import all_docs
from kash.exec.precondition_checks import items_matching_precondition
from kash.model.paths_model import fmt_store_path
from kash.model.preconditions_model import Precondition
from kash.shell.completions.completion_scoring import (
    MIN_CUTOFF,
    normalize,
    score_completions,
    score_items,
    score_paths,
    truncate_completions,
)
from kash.shell.completions.completion_types import (
    COMPLETION_DISPLAY_MAX_LEN,
    CompletionGroup,
    CompletionValue,
    Score,
    ScoredCompletion,
    SortKey,
    SortKeyFn,
)
from kash.utils.common.type_utils import not_none
from kash.workspaces import current_ignore, current_ws

log = get_logger(__name__)

T = TypeVar("T")

MAX_COMPLETIONS = 500

MAX_DIR_COMPLETIONS = 100


def trace_completions_enabled() -> bool:
    from kash.xonsh_custom.load_into_xonsh import XSH

    assert XSH.env
    return bool(XSH.env.get("XONSH_TRACE_COMPLETIONS"))


def trace_completions(msg: str, value: Any = None, always: bool = False):
    def format_value(c: Any) -> str:
        return c.formatted() if isinstance(c, ScoredCompletion) else repr(c)

    if trace_completions_enabled() or always:
        if value and isinstance(value, (list, set)):
            len_suffix = f" ({len(value)} items)"
        else:
            len_suffix = ""
        print(f"COMPLETIONS: {msg}{len_suffix}")
        if value is not None:
            if isinstance(value, (list, set)):
                value = fmt_lines((format_value(c) for c in value), max=30)
                print(value)
            else:
                sys.displayhook(value)
            print()


def sort_scored_and_grouped() -> SortKeyFn:
    """
    Sort completions by group, then by score.
    Prefix matching etc. should all be baked into the score.
    """

    def sortkey(c: ScoredCompletion) -> SortKey:
        return SortKey(
            group=c.group,
            neg_score=Score(-c.score) if c.score else None,
            value=normalize(c),
        )

    return sortkey


def _dir_description(directory: Path) -> str:
    if not directory.exists():
        return ""
    # TODO: Cache, maybe also track size and other info.
    count = sum(1 for _ in directory.glob("*"))
    return f"{count} files"


def all_help_command_completions() -> list[CompletionValue]:
    return [
        CompletionValue(
            group=CompletionGroup.help,
            value=command.__name__,
            display=f"{EMOJI_COMMAND} {command.__name__}",
            description=single_line(command.__doc__ or ""),
            style=STYLE_KASH_COMMAND,
            append_space=True,
        )
        for command in HELP_COMMANDS
    ]


BARE_COMPLETIONS = {
    "help",
    "commands",
    "actions",
    "getting_started",
    "check_system_tools",
    "What is kash?",
    "How can I transcribe a YouTube video?",
}


def get_help_completions_lexical(query: str, include_bare_qm: bool) -> set[ScoredCompletion]:
    query = normalize(query)

    generic_help_completions = []
    if include_bare_qm:
        generic_help_completions.append(
            ScoredCompletion(
                "?",
                display="?",
                description="Ask for assistance.",
                replace_input=True,
                group=CompletionGroup.top_suggestion,
            ),
        )

    snippet_completions = [ScoredCompletion.from_help_doc(c) for c in all_docs.usable_snippets]
    faq_completions = [ScoredCompletion.from_help_doc(c) for c in all_docs.faqs]

    help_command_completions = [
        ScoredCompletion.from_value(
            CompletionValue(
                group=CompletionGroup.help,
                value=command.__name__,
                display=f"{EMOJI_COMMAND} {command.__name__}",
                description=single_line(command.__doc__ or ""),
                style=STYLE_KASH_COMMAND,
                append_space=True,
                replace_input=True,
            )
        )
        for command in HELP_COMMANDS
    ]

    if not query.strip():
        # Handle an empty help completion query with only top help completions.
        all_completions = generic_help_completions + faq_completions + help_command_completions
        # Promote a few to the top.
        for c in all_completions:
            if c.value.lstrip("? ") in BARE_COMPLETIONS:
                c.group = CompletionGroup.top_suggestion

        trace_completions("get_help_completions_lexical: bare query", all_completions)
        return set(all_completions)
    else:
        all_completions = (
            generic_help_completions
            + snippet_completions
            + faq_completions
            + help_command_completions
        )

        score_completions(query, all_completions)
        truncate_completions(all_completions)

        trace_completions("get_help_completions_lexical: regular query", all_completions)
        return set(all_completions)


@tally_calls(level="debug")
def get_help_completions_semantic(query: str) -> set[ScoredCompletion]:
    """
    Semantic lookup of completions from help docs. Requires embededing APIs so
    throws ApiResultError if user is offline or API has issues.
    """
    if len(query) <= 3:
        return set()

    hits = all_docs.help_index.rank_docs(query, max=10, min_cutoff=0.25)
    completions = set(
        ScoredCompletion.from_help_doc(hit.doc, relatedness=hit.relatedness) for hit in hits
    )

    trace_completions("get_help_completions_lexical", completions)
    return completions


def get_command_and_action_completions(prefix: str) -> set[ScoredCompletion]:
    prefix = normalize(prefix)
    completions = [
        ScoredCompletion.from_help_doc(c)
        for c in all_docs.action_infos + all_docs.custom_command_infos
    ]
    score_completions(prefix, completions)
    truncate_completions(completions)
    return set(completions)


def get_std_command_completions(prefix: str) -> set[ScoredCompletion]:
    prefix = normalize(prefix)
    completions = [ScoredCompletion.from_help_doc(c) for c in all_docs.std_command_infos]
    score_completions(prefix, completions)
    truncate_completions(completions)
    return set(completions)


def get_dir_completions(
    prefix: str, base_dir: Path, min_cutoff: Score = MIN_CUTOFF
) -> set[ScoredCompletion]:
    prefix = normalize(prefix)

    is_ignored = current_ignore()
    dirs = (d.relative_to(base_dir) for d in base_dir.iterdir() if d.is_dir() and not is_ignored(d))
    scored_paths = score_paths(prefix, dirs, min_cutoff=min_cutoff)

    return set(
        ScoredCompletion(
            fmt_store_path(d) + "/",
            display=fmt_store_path(d),
            description=_dir_description(d),
            append_space=False,
            score=score,
        )
        for (score, d) in scored_paths
    )


def get_item_completions(
    prefix: str,
    precondition: Precondition = Precondition.always,
    complete_from_global_ws: bool = True,
) -> set[ScoredCompletion] | None:
    prefix = normalize(prefix.lstrip("@"))

    ws = current_ws()
    if ws.is_global_ws and not complete_from_global_ws:
        return None

    # Get immediate subdirectories from workspace base directory.
    dir_completions = get_dir_completions(prefix, ws.base_dir)
    trace_completions(f"Item completions: dir completions: {len(dir_completions)}", dir_completions)

    starts_with_prefix = Precondition(
        lambda item: normalize(str(not_none(item.store_path))).startswith(prefix)
    )

    matching_items = list(
        items_matching_precondition(
            ws, precondition & starts_with_prefix, max_results=MAX_COMPLETIONS
        )
    )
    trace_completions(f"Item completions: matched items: {len(matching_items)}")

    scored_items = score_items(prefix, matching_items, min_cutoff=MIN_CUTOFF, boost_to=MIN_CUTOFF)

    item_completions = set(
        ScoredCompletion(
            fmt_store_path(not_none(item.store_path)),
            # Could include {precondition.name} but not much room here.
            display=abbrev_str(
                f"{fmt_store_path(not_none(item.store_path))}",
                COMPLETION_DISPLAY_MAX_LEN,
            ),
            description=item.abbrev_title(),
            append_space=True,
            score=score,
        )
        for (score, item) in scored_items
    )
    trace_completions(f"Item completions: scored items: {len(scored_items)}", item_completions)

    return dir_completions | item_completions
