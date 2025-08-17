from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from typing import Any, TypeVar

from kash.config.logger import get_logger
from kash.config.settings import global_settings
from kash.shell.output.shell_output import multitask_status
from kash.utils.api_utils.api_retries import RetrySettings
from kash.utils.api_utils.gather_limited import FuncTask, Limit, gather_limited_sync

T = TypeVar("T")

log = get_logger(name=__name__)


def _default_labeler(total: int) -> Callable[[int, Any], str]:
    def labeler(i: int, _spec: Any) -> str:  # pyright: ignore[reportUnusedParameter]
        return f"Task {i + 1}/{total}"

    return labeler


async def multitask_gather(
    tasks: Iterable[FuncTask[T]] | Sequence[FuncTask[T]],
    *,
    labeler: Callable[[int, Any], str] | None = None,
    limit: Limit | None = None,
    bucket_limits: dict[str, Limit] | None = None,
    retry_settings: RetrySettings | None = None,
    show_progress: bool = True,
) -> list[T]:
    """
    Run many `FuncTask`s concurrently with shared progress UI and rate limits.

    This wraps the standard pattern of creating a status context, providing a labeler,
    and calling `gather_limited_sync` with common options.

    - `labeler` can be omitted; a simple "Task X/Y" label will be used.
    - If `limit` is not provided, defaults are taken from `global_settings()`.
    - If `show_progress` is False, tasks are run without the status context.
    - By default, exceptions are returned as results rather than raised (return_exceptions=True).
    """

    # Normalize tasks to a list for length and stable iteration
    task_list: list[FuncTask[T]] = list(tasks)

    # Provide a default labeler if none is supplied
    effective_labeler: Callable[[int, Any], str] = (
        labeler if labeler is not None else _default_labeler(len(task_list))
    )

    # Provide sensible default rate limits if none are supplied
    effective_limit: Limit = (
        limit
        if limit is not None
        else Limit(
            rps=global_settings().limit_rps,
            concurrency=global_settings().limit_concurrency,
        )
    )

    if not show_progress:
        log.warning("Running %d tasks (progress disabled)…", len(task_list))

    async with multitask_status(enabled=show_progress) as status:
        return await gather_limited_sync(
            *task_list,
            limit=effective_limit,
            bucket_limits=bucket_limits,
            status=status,
            labeler=effective_labeler,
            retry_settings=retry_settings,
        )
