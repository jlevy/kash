from __future__ import annotations

import math
import re
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import TypeVar

from strif import abbrev_str
from thefuzz import fuzz

from kash.config.logger import get_logger
from kash.exec_model.commands_model import CommentedCommand
from kash.help.help_types import HelpDocType, RecipeSnippet
from kash.model.items_model import Item
from kash.shell.completions.completion_types import Score, ScoredCompletion
from kash.utils.common.type_utils import not_none

log = get_logger(__name__)

T = TypeVar("T")

# Scores less than this can be dropped early.
MIN_CUTOFF = Score(60)


def linear_boost(score: Score, min_score: Score) -> Score:
    """
    Boost score linearly: [0, 100] -> [boost_min, 100]
    """
    scaling_factor = (100 - min_score) / 100
    return Score(min_score + (score * scaling_factor))


def score_completions(
    query: str,
    completions: Iterable[ScoredCompletion],
    subphrase_min_words: int = 4,
    incomplete_discount: float = 0.8,
    semantic_boost: float = 2.0,
) -> None:
    """
    Score completions in place based on a query. If `loose_subphrase` is set, allow any
    subphrase match (good for FAQs etc). Otherwise does the default of balancing prefix
    and subphrase matches.
    """
    for completion in completions:
        # Only score completions that aren't already scored.
        if completion.score:
            continue

        normalized_value = normalize(str(completion.value))

        exact_prefix = score_exact_prefix(query, normalized_value)
        phrase = score_phrase(query, normalized_value)

        score = max(exact_prefix, incomplete_discount * phrase)

        # Boost completions with high relatedness.
        if completion.relatedness:
            score += Score(completion.relatedness * 100 * semantic_boost)

        # For FAQs and recipe snippets, allow loose subphrase matches, but not for very short queries.
        use_loose_subphrase = (
            completion.help_doc
            and completion.help_doc.doc_type
            in (
                HelpDocType.faq,
                HelpDocType.recipe_snippet,
            )
            and len(query.split()) > subphrase_min_words
        )
        if use_loose_subphrase:
            score = max(score, incomplete_discount * score_subphrase(query, normalized_value))

        # Boost completions with descriptions (means we have tldr docs and are likely more useful).
        if (
            completion.help_doc
            and completion.help_doc.doc_type == HelpDocType.command_info
            and completion.description
        ):
            score = score + 5

        score = min(score, 100)

        completion.score = Score(score)


def truncate_completions(
    completions: list[ScoredCompletion], min_cutoff: Score = MIN_CUTOFF
) -> None:
    """
    Truncate completions in place, dropping any already scored below the min score.
    """
    truncated_completions = []
    for completion in completions:
        if completion.score and completion.score >= min_cutoff:
            truncated_completions.append(completion)

    completions[:] = truncated_completions


def get_scored_snippet_completions(
    snippets: Iterable[RecipeSnippet],
    query: str,
    max_results: int = 10,
    min_cutoff: Score = MIN_CUTOFF,
) -> list[ScoredCompletion]:
    """
    Suggest snippets for a given query, sorted by relevance.
    """

    if not query.strip() or not snippets:
        return []

    # Score all snippets.
    scored_snippets = [(score_snippet(query, snippet.command), snippet) for snippet in snippets]

    # Sort by score descending.
    scored_snippets.sort(key=lambda x: x[0], reverse=True)

    return [
        ScoredCompletion(
            snippet.command.command_line,
            display=abbrev_str(snippet.command.command_line, max_len=40),
            description=snippet.command.comment or "",
            append_space=True,
            replace_input=True,  # Snippets should replace the entire input.
        )
        for score, snippet in scored_snippets[:max_results]
        if score >= min_cutoff
    ]


# For reference: xonsh's default Completer normalization.
# def normalize_xonsh(s: str) -> str:
#     s = str(s).lower().strip().lstrip("'\"")
#     if s.startswith("$"):
#         s = s[1:]
#     return s

_punct_re = re.compile(r"[^\w\s]")


def normalize(text: str) -> str:
    return _punct_re.sub(" ", text.lower()).strip()


def score_exact_prefix(prefix: str, text: str) -> Score:
    """
    A prefix match scores high, but even higher if it's more of the text and for
    longer matches.
    """
    if not text.startswith(prefix):
        return Score(0)

    prefix_len = len(prefix)
    if prefix_len < 2:
        return Score(50)

    completion_ratio = prefix_len / len(text)
    long_prefix_bonus = prefix_len - 2
    score = 70 + (20 * completion_ratio) + min(10, long_prefix_bonus)

    return Score(score)


def score_phrase(prefix: str, text: str) -> Score:
    """
    Could experiment with this more but it's a rough attempt to balance
    full matches and prefix matches.
    """
    return Score(
        0.4 * fuzz.token_set_ratio(prefix, text)
        + 0.4 * fuzz.partial_ratio(prefix, text)
        + 0.2 * fuzz.token_sort_ratio(prefix, text)
    )


def score_subphrase(prefix: str, text: str) -> Score:
    """
    Score a subphrase match, blending character and token set scoring.
    """
    return Score(
        0.5 * fuzz.partial_ratio(prefix, text) + 0.5 * fuzz.partial_token_set_ratio(prefix, text)
    )


def score_path(prefix: str, path: Path, timestamp: datetime | None = None) -> Score:
    """
    Score a path completion, blending prefix matches, phrase matches, and recency.
    """
    path_str = normalize(str(path))
    name_str = normalize(path.name)

    # Get timestamp and a recency score.
    recency = 0.0
    if not timestamp:
        try:
            timestamp = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
        except FileNotFoundError:
            timestamp = None
    if timestamp:
        age = (datetime.now(UTC) - timestamp).total_seconds()
        recency = decaying_recency(age)

    # Exact prefixes are often what we want to score separately.
    exact_prefix_score = max(
        score_exact_prefix(prefix, path_str), score_exact_prefix(prefix, name_str)
    )

    # For approx matches, use a blended prefix and full match along with recency.
    path_score = max(score_phrase(prefix, path_str), score_phrase(prefix, name_str))
    approx_match_score = 0.7 * path_score + 0.3 * recency

    return Score(max(exact_prefix_score, approx_match_score))


ONE_HOUR = 3600
ONE_YEAR = 3600 * 24 * 365


def decaying_recency(
    age_in_seconds: float, min_age_sec: float = ONE_HOUR, max_age_sec: float = ONE_YEAR
) -> Score:
    """
    Calculate a score (0-100) based on last use or modification time.
    Uses an exponential decay curve to give higher weights to more recent changes.
    """
    if age_in_seconds <= min_age_sec:
        return Score(100.0)
    if age_in_seconds >= max_age_sec:
        return Score(0.0)

    age_after_min = age_in_seconds - min_age_sec
    time_range = max_age_sec - min_age_sec

    decay_constant = 5.0 / time_range

    return Score(100.0 * math.exp(-decay_constant * age_after_min))


def score_paths(prefix: str, paths: Iterable[Path], min_cutoff: Score) -> list[tuple[Score, Path]]:
    scored_paths = [(score_path(prefix, p), p) for p in paths]
    scored_paths = [(score, p) for score, p in scored_paths if score >= min_cutoff]
    scored_paths.sort(key=lambda x: x[0], reverse=True)
    return scored_paths


def score_items(
    prefix: str, items: Iterable[Item], min_cutoff: Score, boost_to: Score = Score(0.0)
) -> list[tuple[Score, Item]]:
    def score_item(prefix: str, item: Item) -> Score:
        timestamp = item.modified_at or item.created_at or None
        return linear_boost(
            score_path(prefix, Path(not_none(item.store_path)), timestamp), boost_to
        )

    scored_items = [(score_item(prefix, item), item) for item in items]
    scored_items = [(score, item) for score, item in scored_items if score >= min_cutoff]
    scored_items.sort(key=lambda x: x[0], reverse=True)
    return scored_items


def score_snippet(query: str, snippet: CommentedCommand) -> Score:
    # FIXME: Add embedding scoring.

    normalized_query = normalize(query)
    normalized_command = normalize(snippet.command_line)
    normalized_comment = normalize(snippet.comment or "")

    # Score the command and comment separately.
    command_score = max(
        score_phrase(normalized_query, normalized_command),
        score_subphrase(normalized_query, normalized_command),
    )
    comment_score = max(
        score_phrase(normalized_query, normalized_comment),
        score_subphrase(normalized_query, normalized_comment),
    )
    # Bias a little toward command matches.
    return Score(max(command_score, 0.7 * comment_score))
