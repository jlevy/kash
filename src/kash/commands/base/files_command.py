from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from prettyfmt import fmt_path, fmt_size_human, fmt_time
from rich.text import Text

from kash.commands.workspace.selection_commands import select
from kash.config.logger import get_logger
from kash.config.settings import global_settings
from kash.config.text_styles import COLOR_EXTRA, EMOJI_WARN, STYLE_EMPH, STYLE_HINT, colorize_qty
from kash.exec import kash_command
from kash.exec_model.shell_model import ShellResult
from kash.local_server.local_url_formatters import local_url_formatter
from kash.model.items_model import Item, ItemType
from kash.model.paths_model import StorePath, parse_path_spec
from kash.shell.file_icons.color_for_format import color_for_format
from kash.shell.output.shell_output import PrintHooks, Wrap, console_pager, cprint
from kash.utils.file_utils.file_formats_model import Format, guess_format_by_name
from kash.utils.file_utils.file_sort_filter import (
    FileInfo,
    FileListing,
    FileType,
    GroupByOption,
    SortOption,
    collect_files,
    parse_since,
    type_suffix,
)
from kash.utils.file_utils.ignore_files import ignore_none
from kash.utils.file_utils.path_utils import common_parent_dir
from kash.workspaces import current_ignore, current_ws

log = get_logger(__name__)


def _print_listing_tallies(
    file_listing: FileListing,
    total_displayed: int,
    total_displayed_size: int,
    max_files: int,
    max_depth: int,
    max_per_subdir: int,
) -> None:
    if total_displayed > 0:
        cprint(
            f"{total_displayed} files ({fmt_size_human(total_displayed_size)}) shown",
            style=COLOR_EXTRA,
        )
    if file_listing.files_total > file_listing.files_matching > total_displayed:
        cprint(
            f"of {file_listing.files_matching} files "
            f"({fmt_size_human(file_listing.size_matching)}) matching criteria",
            style=COLOR_EXTRA,
        )
    if file_listing.files_total > total_displayed:
        cprint(
            f"from {file_listing.files_total} total files "
            f"({fmt_size_human(file_listing.size_total)})",
            style=COLOR_EXTRA,
        )
    if file_listing.total_ignored > 0:
        cprint(
            f"{EMOJI_WARN} {file_listing.files_ignored} files and {file_listing.dirs_ignored} dirs were ignored",
            style=COLOR_EXTRA,
        )
        cprint("(use --no_ignore to show hidden files)", style=STYLE_HINT)

    if file_listing.total_skipped > 0:
        cprint(
            f"{EMOJI_WARN} long file listing: capped "
            f"at max_files={max_files}, max_depth={max_depth}, max_per_subdir={max_per_subdir}",
            style=COLOR_EXTRA,
        )
        cprint("(use --no_max to remove cutoff)", style=STYLE_HINT)


@kash_command
def files(
    *paths: str,
    overview: bool = False,
    recent: bool = False,
    recursive: bool = False,
    flat: bool = False,
    pager: bool = False,
    omit_dirs: bool = False,
    max_per_group: int = -1,
    depth: int | None = None,
    max_per_subdir: int = 1000,
    max_files: int = 1000,
    no_max: bool = False,
    no_ignore: bool = False,
    all: bool = False,
    save: bool = False,
    sort: SortOption | None = None,
    reverse: bool = False,
    since: str | None = None,
    groupby: GroupByOption | None = GroupByOption.parent,
    iso_time: bool = False,
) -> ShellResult:
    """
    List files or folders in the current directory or specified paths.

    Attempts to be similar to `ls` or `eza` but without any legacy constraints.

    Aims for simple output, optional paging, a better "overview" mode that recurses
    with limited depth and breadth, and more control over recursion, sorting,
    and grouping.

    :param overview: Recurse a couple levels and show files, but not too many.
        Same as `--groupby=parent --depth=2 --max_per_group=10 --omit_dirs`.
    :param recent: Only shows the most recently modified files in each directory.
        Same as `--sort=modified --reverse --groupby=parent --max_per_group=10`.
    :param recursive: List all files recursively. Same as `--depth=-1`.
    :param flat: Show files in a flat list, rather than grouped by parent directory.
        Same as `--groupby=flat`.
    :param omit_dirs: Normally directories are included. This option omits them,
        which is useful when recursing into subdirectories.
    :param depth: Maximum depth to recurse into directories. -1 means no limit.
    :param max_files: Maximum number of files to yield per input path.
        -1 means no limit.
    :param max_per_subdir: Maximum number of files to yield per subdirectory
        (not including the top level). -1 means no limit.
    :param max_per_group: Limit the first number of items displayed per group
        (if groupby is used) or in total. 0 means show all.
    :param no_max: Disable limits on depth and number of files. Same as
        `--depth=-1 --max_files=-1 --max_per_subdir=-1 --max_per_group=-1`.
    :param no_ignore: Disable ignoring hidden files.
    :param all: Same as `--no_ignore --no_max`. Does not change `--depth`.
    :param save: Save the listing as a CSV file item.
    :param sort: Sort by `filename`, `size`, `accessed`, `created`, or `modified`.
    :param reverse: Reverse the sorting order.
    :param since: Filter files modified since a given time (e.g., '1 day', '2 hours').
    :param groupby: Group results. Can be `flat` (no grouping, and by default implies
        recursive), `parent`, or `suffix`. Defaults to 'parent'.
    :param iso_time: Show time in ISO format (default is human-readable age).
    :param pager: Use the pager when displaying the output.
    """
    if global_settings().use_nerd_icons:
        from kash.shell.file_icons.nerd_icons import icon_for_file
    else:
        icon_for_file = None

    # TODO: Add a --full option with line and word counts and file_info details
    # and also include these in --save.

    if len(paths) == 0:
        paths_to_show = [Path(".")]
        no_explicit_paths = True
    else:
        paths_to_show = [parse_path_spec(path) for path in paths]
        no_explicit_paths = False

    # Set up base path. If we have a workspace and if this listing is within the
    # current workspace, detect that, since it's convenient to enable brief listings
    # in workspaces.
    cwd = Path.cwd()
    ws = current_ws()
    active_ws_name = ws.name if cwd.is_relative_to(ws.base_dir.resolve()) else None
    # Check if all requested paths are within the current directory, and if so use
    # that as the base path. Otherwise, use the common parent directory of all paths.
    if paths_to_show:
        base_path = common_parent_dir(*paths_to_show)
        if base_path.is_relative_to(cwd):
            base_path = cwd
        within_cwd = base_path.is_relative_to(cwd)
    else:
        base_path = Path(".")
        within_cwd = True
    # Should we show absolute paths?
    show_absolute_paths = not within_cwd
    # Is this a listing of the current workspace?
    is_ws_listing = active_ws_name and ws.base_dir.resolve() == base_path.resolve()

    # Handle lots of different options.
    if recursive:
        depth = -1
    if is_ws_listing and no_explicit_paths:
        # Within workspaces, we show more files by default since they are always in
        # subdirectories.
        overview = True  # Handled next.
    if overview:
        max_per_group = 10 if max_per_group <= 0 else max_per_group
        groupby = GroupByOption.parent if groupby is None else groupby
        depth = 2 if depth is None else depth
        omit_dirs = True
    if recent:
        max_per_group = 10 if max_per_group <= 0 else max_per_group
        groupby = GroupByOption.parent if groupby is None else groupby
        depth = 2 if depth is None else depth
        sort = SortOption.modified if sort is None else sort
        reverse = True
    if flat:
        groupby = GroupByOption.flat
    if all:
        no_ignore = True
        no_max = True
    if no_max:
        depth = max_per_subdir = max_per_group = max_files = -1
    # Unless depth is specified, flat implies recursive (depth -1).
    if groupby == GroupByOption.flat and depth is None:
        depth = -1

    # Default depth unless otherwise set or implied is 0 (like ls).
    depth = 0 if depth is None else depth

    since_seconds = parse_since(since) if since else 0.0

    # Determine whether to show hidden files for this path.
    is_ignored = current_ignore()
    if no_ignore:
        is_ignored = ignore_none
    else:
        for path in paths_to_show:
            # log.info("Checking ignore for %s against filter %s", fmt_path(path), is_ignored)
            if not no_ignore and is_ignored(path, is_dir=path.is_dir()):
                log.info(
                    "Requested path is on the ignore list so disabling ignore: %s",
                    fmt_path(path),
                )
                is_ignored = ignore_none
                break

    # Collect all the files.
    log.debug(
        "Collecting files: %s",
        {
            "paths_to_show": paths_to_show,
            "depth": depth,
            "max_per_subdir": max_per_subdir,
            "max_per_group": max_per_group,
            "max_files": max_files,
            "omit_dirs": omit_dirs,
            "since_seconds": since_seconds,
            "base_path": base_path,
            "include_dirs": not omit_dirs,
        },
    )
    file_listing = collect_files(
        start_paths=paths_to_show,
        ignore=is_ignored,
        since_seconds=since_seconds,
        max_depth=depth,
        max_files_per_subdir=max_per_subdir,
        max_files_total=max_files,
        base_path=base_path,
        include_dirs=not omit_dirs,
        resolve_parent=show_absolute_paths,
    )

    log.info("Collected %s files.", file_listing.files_total)

    if not file_listing.files:
        cprint("No files found.")
        PrintHooks.spacer()
        _print_listing_tallies(file_listing, 0, 0, max_files, depth, max_per_subdir)
        return ShellResult()

    df = file_listing.as_dataframe()

    if sort:
        # Determine the primary and secondary sort columns.
        primary_sort = sort.value
        secondary_sort = "filename" if primary_sort != "filename" else "created"

        df.sort_values(
            by=[primary_sort, secondary_sort], ascending=[not reverse, True], inplace=True
        )

    items_matching = len(df)
    log.info(f"Total items collected: {items_matching}")

    if groupby and groupby != GroupByOption.flat:
        grouped = df.groupby(groupby.value)
    else:
        grouped = [(None, df)]

    if save:
        item = Item(
            type=ItemType.export,
            title="File Listing",
            description=f"Files in {', '.join(fmt_path(p) for p in paths_to_show)}",
            format=Format.csv,
            body=df.to_csv(index=False),
        )
        ws = current_ws()
        store_path = ws.save(item, as_tmp=False)
        log.message("File listing saved to: %s", fmt_path(store_path))

        select(store_path)

        return ShellResult(show_selection=True)

    total_displayed = 0
    total_displayed_size = 0
    now = datetime.now(UTC)

    # Define spacing constants.
    TIME_WIDTH = 12
    SIZE_WIDTH = 8
    SPACING = "  "
    indent = " " * (TIME_WIDTH + SIZE_WIDTH + len(SPACING) * 2)

    with console_pager(use_pager=pager):
        with local_url_formatter(active_ws_name) as fmt:
            for group_name, group_df in grouped:
                # If items are grouped e.g. by parent directory, show the group name first.
                if group_name:
                    cprint(
                        f"{group_name} ({len(group_df)} files)",
                        style=STYLE_EMPH,
                        text_wrap=Wrap.NONE,
                    )

                if max_per_group > 0:
                    display_df = group_df.head(max_per_group)
                else:
                    display_df = group_df

                for row in display_df.itertuples(index=False, name="FileInfo"):
                    row = cast(FileInfo, row)  # pyright: ignore
                    short_file_size = fmt_size_human(row.size)
                    full_file_size = f"{row.size} bytes"
                    short_mod_time = fmt_time(row.modified, iso_time=iso_time, now=now, brief=True)
                    full_mod_time = fmt_time(row.modified, friendly=True, now=now)
                    is_dir = row.type == FileType.dir

                    rel_path = str(row.relative_path)

                    # If we are listing from within a workspace and we are at the base
                    # of the workspace, we include the paths as store paths (with an @
                    # prefix). Otherwise, use regular paths.
                    if is_ws_listing:
                        display_path = StorePath(rel_path)  # Add a local server link.
                        display_path_str = f"{display_path}{type_suffix(row)}"
                    else:
                        display_path = Path(rel_path)
                        display_path_str = f"{display_path}{type_suffix(row)}"

                    # Assemble output line.
                    line: list[str | Text] = []
                    line.append(
                        colorize_qty(
                            fmt.tooltip_link(
                                short_mod_time.rjust(TIME_WIDTH), tooltip=full_mod_time
                            )
                        )
                    )
                    line.append(SPACING)
                    if is_dir:
                        # TODO: Insert tallies of files/total size in a fast/efficient way.
                        line.append(" " * SIZE_WIDTH)
                    else:
                        line.append(
                            colorize_qty(
                                fmt.tooltip_link(
                                    short_file_size.rjust(SIZE_WIDTH), tooltip=full_file_size
                                )
                            )
                        )
                    line.append(SPACING)
                    if icon_for_file:
                        icon = icon_for_file(rel_path, is_dir=is_dir)
                        color = color_for_format(guess_format_by_name(rel_path))
                        line.append(
                            fmt.tooltip_link(icon.icon_char, tooltip=icon.readable, style=color)
                        )
                        line.append(" ")
                    line.append(
                        fmt.path_link(
                            display_path,
                            link_text=display_path_str,
                        ),
                    )

                    cprint(Text.assemble(*line), text_wrap=Wrap.NONE)
                    total_displayed += 1
                    total_displayed_size += row.size

                # Indicate if items are omitted.
                if groupby and max_per_group > 0 and len(group_df) > max_per_group:
                    cprint(
                        f"{indent}… and {len(group_df) - max_per_group} more files",
                        style=COLOR_EXTRA,
                        text_wrap=Wrap.NONE,
                    )

                if group_name:
                    PrintHooks.spacer()

            if not groupby and max_per_group > 0 and items_matching > max_per_group:
                cprint(
                    f"{indent}… and {items_matching - max_per_group} more files",
                    style=COLOR_EXTRA,
                    text_wrap=Wrap.NONE,
                )

            PrintHooks.spacer()
            _print_listing_tallies(
                file_listing,
                total_displayed,
                total_displayed_size,
                max_files,
                depth,
                max_per_subdir,
            )

    return ShellResult()
