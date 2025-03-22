import time
from collections.abc import Iterator
from typing import Any

from funlog import format_duration
from typing_extensions import override
from xonsh.completer import Completer
from xonsh.parsers.completion_context import CompletionContext

from kash.config.logger import get_logger
from kash.help.tldr_help import tldr_description
from kash.shell.completions.completion_scoring import normalize, score_completions
from kash.shell.completions.completion_types import ScoredCompletion
from kash.shell.completions.shell_completions import (
    sort_scored_and_grouped,
    trace_completions,
    trace_completions_enabled,
)

log = get_logger(__name__)


class RankingCompleter(Completer):
    """
    Custom completer that overrides default xonsh behavior to provide better
    control over completion ranking and deduplication.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.trace_enabled: bool = trace_completions_enabled()

    @override
    def complete_from_context(
        self, completion_context: CompletionContext, old_completer_args: Any = None
    ) -> tuple[tuple[ScoredCompletion, ...], int]:
        start_time = time.time()
        self._trace("complete_from_context: Getting completions with context", completion_context)

        # Collect all completions.
        completions = list(self._collect_completions(completion_context, old_completer_args))
        duration = time.time() - start_time
        trace_completions(
            f"complete_from_context: Collecting completions took {format_duration(duration)}",
            completions,
        )

        # Deduplicate.
        self._deduplicate_completions(completions)

        # Enrich standard xonsh completions with any changes/additions.
        self._enrich_completions(completions)

        # Score any still-unscored completions (mainly those from xonsh's built-in completers).
        self._score_unscored_completions(completions, completion_context)

        # Rank.
        self._rank_completions(completions, completion_context)

        # lprefix is the length of the prefix of the last completion.
        lprefix = len(completions[0].value) if completions else 0

        duration = time.time() - start_time
        trace_completions(
            f"complete_from_context: Total time: {format_duration(duration)} (lprefix={lprefix!r})",
            completions,
        )

        return tuple(completions), lprefix

    def _collect_completions(
        self, completion_context: CompletionContext, old_completer_args: Any
    ) -> Iterator[ScoredCompletion]:
        """
        Collect completions from all registered completers. Ensure all are
        RichCompletions. This does some preliminary truncation of useless results
        but doesn't do final sorting.
        """
        for completion, _prefix_len in self.generate_completions(
            completion_context, old_completer_args, trace=self.trace_enabled
        ):
            if not isinstance(completion, ScoredCompletion):
                completion = ScoredCompletion.from_unscored(completion)
            yield completion

    def _deduplicate_completions(self, completions: list[ScoredCompletion]) -> None:
        """
        Deduplicate completions while preserving order.
        """

        seen_values = set()
        deduped_completions = []
        for completion in completions:
            c_str = normalize(completion)
            if c_str not in seen_values:
                seen_values.add(c_str)
                deduped_completions.append(completion)

        if len(deduped_completions) < len(completions):
            self._trace(
                f"_deduplicate_complettions: Deduplicated completions kept {len(deduped_completions)}/{len(completions)}:",
                deduped_completions,
            )
        else:
            self._trace(
                f"_deduplicate_completions: No dups found in {len(completions)} completions."
            )

        completions[:] = deduped_completions

    def _enrich_completions(self, completions: list[ScoredCompletion]):
        """
        Adjust the completions (could be kash completions or standard xonsh completions)
        with additional information.
        """
        # This disables the default xonsh behavior of stripping a common prefix. It seems
        # less confusing without it.
        for completion in completions:
            if not completion.display:
                completion.display = completion.value

        # Add command descriptions from tldr.
        for completion in completions:
            command = completion.value.strip()
            if not completion.description:
                description = tldr_description(command)
                if description:
                    completion.description = description

        # TODO: Could also enrich with emojis for display.

    def _score_unscored_completions(
        self, completions: list[ScoredCompletion], context: CompletionContext
    ):
        if context and context.command:
            prefix = normalize(context.command.prefix)
            if prefix:
                score_completions(prefix, completions)

    def _rank_completions(
        self,
        completions: list[ScoredCompletion],
        _context: CompletionContext,
    ) -> None:
        sortkey = sort_scored_and_grouped()
        completions.sort(key=sortkey)

        if self.trace_enabled:
            self._trace("_rank_completions: After ranking", completions)

    def _trace(self, msg: str, value: Any = None):
        trace_completions(msg, value)
