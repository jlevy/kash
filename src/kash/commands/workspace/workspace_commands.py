import os
from pathlib import Path

from frontmatter_format import to_yaml_string
from prettyfmt import fmt_lines
from rich.text import Text

from kash.commands.base.basic_file_commands import trash
from kash.commands.base.files_command import files
from kash.commands.workspace.selection_commands import select
from kash.config.logger import get_logger
from kash.config.settings import global_settings
from kash.config.text_styles import (
    COLOR_SUGGESTION,
    EMOJI_WARN,
    STYLE_EMPH,
    STYLE_HINT,
    format_success_emoji,
)
from kash.exec import (
    assemble_path_args,
    assemble_store_path_args,
    kash_command,
    resolve_locator_arg,
)
from kash.exec.action_registry import get_all_actions_defaults
from kash.exec.fetch_url_metadata import fetch_url_metadata
from kash.exec.precondition_checks import actions_matching_paths
from kash.exec.precondition_registry import get_all_preconditions
from kash.exec.preconditions import is_url_item
from kash.exec_model.shell_model import ShellResult
from kash.local_server.local_url_formatters import local_url_formatter
from kash.media_base import media_tools
from kash.media_base.media_services import is_media_url
from kash.model.items_model import Item, ItemType
from kash.model.params_model import GLOBAL_PARAMS
from kash.model.paths_model import StorePath, fmt_store_path
from kash.shell.input.param_inputs import input_param_name, input_param_value
from kash.shell.output.shell_output import (
    PrintHooks,
    Wrap,
    console_pager,
    cprint,
    format_name_and_description,
    format_name_and_value,
    print_h2,
    print_h3,
    print_status,
)
from kash.shell.utils.native_utils import tail_file
from kash.utils.common.format_utils import fmt_loc
from kash.utils.common.obj_replace import remove_values
from kash.utils.common.parse_key_vals import parse_key_value
from kash.utils.common.type_utils import not_none
from kash.utils.common.url import Url, is_url
from kash.utils.errors import InvalidInput
from kash.utils.file_formats.chat_format import tail_chat_history
from kash.utils.file_utils.dir_size import is_nonempty_dir
from kash.utils.lang_utils.inflection import plural
from kash.web_content.file_cache_utils import cache_file
from kash.workspaces import (
    current_ws,
    get_global_ws,
    global_ws_dir,
    resolve_ws,
)
from kash.workspaces.param_state import ParamState
from kash.workspaces.workspaces import Workspace, check_strict_workspace_name, get_ws

log = get_logger(__name__)


@kash_command
def clear_global_ws() -> None:
    """
    Clear the entire global_ws by moving it to the trash.
    Use with caution!
    """
    trash(global_ws_dir())
    ws = get_global_ws()
    ws.reload()
    ws.log_workspace_info()


def _get_cache_dirs(workspace: str | None) -> tuple[Path, Path]:
    if workspace:
        ws = get_ws(workspace)
        media_cache = (ws.base_dir / ws.dirs.media_cache_dir).resolve()
        content_cache = (ws.base_dir / ws.dirs.content_cache_dir).resolve()
    else:
        settings = global_settings()
        media_cache = settings.media_cache_dir.resolve()
        content_cache = settings.content_cache_dir.resolve()

    return media_cache, content_cache


@kash_command
def cache_list(media: bool = False, content: bool = False, workspace: str | None = None) -> None:
    """
    List the contents of the workspace media and content caches. By default lists both caches.

    :param media: List media cache only.
    :param content: List content cache only.
    """
    if not media and not content:
        media = True
        content = True

    media_cache, content_cache = _get_cache_dirs(workspace)

    if media:
        if is_nonempty_dir(media_cache):
            files(media_cache, depth=3, omit_dirs=True)
            PrintHooks.spacer()
        else:
            cprint("Media cache is empty: %s", fmt_loc(media_cache))
            PrintHooks.spacer()

    if content:
        if is_nonempty_dir(content_cache):
            files(content_cache, depth=3, omit_dirs=True)
            PrintHooks.spacer()
        else:
            cprint("Content cache is empty: %s", fmt_loc(content_cache))
            PrintHooks.spacer()


@kash_command
def clear_cache(media: bool = False, content: bool = False, workspace: str | None = None) -> None:
    """
    Clear the media and content caches. By default clears both caches.

    :param media: Clear media cache only.
    :param content: Clear content cache only.
    :param global_cache: If in a workspace, clear the global caches, not the workspace caches.
    """
    if not media and not content:
        media = True
        content = True

    media_cache, content_cache = _get_cache_dirs(workspace)

    if media and is_nonempty_dir(media_cache):
        trash(media_cache)
    else:
        cprint("Media cache is empty: %s", fmt_loc(media_cache))
        PrintHooks.spacer()

    if content and is_nonempty_dir(content_cache):
        trash(content_cache)
    else:
        cprint("Content cache is empty: %s", fmt_loc(content_cache))
        PrintHooks.spacer()


@kash_command
def cache_media(*urls: str) -> None:
    """
    Cache media at the given URLs in the media cache, using a tools for the appropriate
    service (yt-dlp for YouTube, Apple Podcasts, etc).
    """
    PrintHooks.spacer()
    for url_str in urls:
        url = Url(url_str)
        cached_paths = media_tools.cache_media(url)
        cprint(f"{url}:", style=STYLE_EMPH, text_wrap=Wrap.NONE)
        for media_type, path in cached_paths.items():
            cprint(f"{media_type.name}: {fmt_loc(path)}", text_wrap=Wrap.INDENT_ONLY)
        PrintHooks.spacer()


@kash_command
def cache_content(*urls_or_paths: str) -> None:
    """
    Cache the given file in the content cache. Downloads any URL or copies a local file.
    """
    PrintHooks.spacer()
    for url_or_path in urls_or_paths:
        locator = resolve_locator_arg(url_or_path)
        cache_path, was_cached = cache_file(locator)
        cache_str = " (already cached)" if was_cached else ""
        cprint(f"{fmt_loc(url_or_path)}{cache_str}:", style=STYLE_EMPH, text_wrap=Wrap.NONE)
        cprint(f"{cache_path}", text_wrap=Wrap.INDENT_ONLY)
        PrintHooks.spacer()


@kash_command
def download(*urls_or_paths: str) -> None:
    """
    Download a URL or resource. Inputs can be URLs or paths to URL resources.
    """
    # TODO: Add option to include frontmatter metadata for text files.
    ws = current_ws()
    for url_or_path in urls_or_paths:
        locator = resolve_locator_arg(url_or_path)
        url = None
        if not isinstance(locator, Path) and is_url(locator):
            url = Url(locator)
        if isinstance(locator, StorePath):
            url_item = ws.load(locator)
            if is_url_item(url_item):
                url = url_item.url
        if not url:
            raise InvalidInput(f"Not a URL or URL resource: {fmt_loc(locator)}")

        if is_media_url(url):
            store_path = ws.import_item(locator, as_type=ItemType.resource)
            log.message(
                "URL is a media URL, so added as a resource and will cache media: %s", fmt_loc(url)
            )
            media_tools.cache_media(url)
        else:
            log.message("Will cache file and save to workspace: %s", fmt_loc(url))
            cache_path, _was_cached = cache_file(url)
            item = Item.from_external_path(cache_path, item_type=ItemType.resource)
            store_path = ws.save(item)

        log.info("Saved item to workspace: %s", fmt_loc(store_path))


@kash_command
def history(max: int = 30, raw: bool = False) -> None:
    """
    Show the kash command history for the current workspace.

    For xonsh's built-in history, use `xhistory`.

    :param max: Show at most the last `max` commands.
    :param raw: Show raw command history by tailing the history file directly.
    """
    # TODO: Customize this by time frame.
    ws = current_ws()
    history_file = ws.base_dir / ws.dirs.shell_history_yml
    chat_history = tail_chat_history(history_file, max)

    if raw:
        tail_file(history_file)
    else:
        n = len(chat_history.messages)
        for i, message in enumerate(chat_history.messages):
            cprint(
                Text("% 4d:" % (i - n), style=STYLE_HINT)
                + Text(f" `{message.content}`", style=COLOR_SUGGESTION),
                text_wrap=Wrap.NONE,
            )


@kash_command
def global_ws() -> None:
    """Change directory to the global_ws workspace."""
    ws = get_global_ws()
    print_status(f"Now in global_ws workspace: {ws.base_dir}")
    os.chdir(ws.base_dir)


@kash_command
def clear_history() -> None:
    """
    Clear the kash command history for the current workspace. Old history file will be
    moved to the trash.
    """
    ws = current_ws()
    trash(ws.base_dir / ws.dirs.shell_history_yml)


@kash_command
def init_workspace(path: str | None = None) -> None:
    """
    Initialize a new workspace at the given path, or in the current directory if no path
    given. If a path is provided, also chdir to the new path.
    """
    base_dir = path or Path(".")
    get_ws(base_dir, auto_init=True)
    os.chdir(base_dir)
    current_ws(silent=True).log_workspace_info()


@kash_command
def workspace(workspace_name: str | None = None) -> None:
    """
    If no args are given, change directory to the current workspace.
    If a workspace name is given, change to that workspace, creating it if it doesn't exist.
    """
    if workspace_name:
        info = resolve_ws(workspace_name)
        name = info.name
        if not info.base_dir.exists():
            # Enforce reasonable naming on new workspaces.
            name = check_strict_workspace_name(name)

        os.makedirs(info.base_dir, exist_ok=True)
        os.chdir(info.base_dir)
        ws = get_ws(name_or_path=info.base_dir, auto_init=True)
        print_status(f"Changed to workspace: {ws.name} ({ws.base_dir})")
        ws.log_workspace_info()
    else:
        ws = current_ws(silent=True)
        os.chdir(ws.base_dir)
        ws.log_workspace_info()


@kash_command
def reload_workspace() -> None:
    """
    Reload the current workspace. Helpful for debugging to reset in-memory state.
    """
    current_ws().reload()


@kash_command
def item_id(*paths: str) -> None:
    """
    Show the item id for the given paths. This is the unique identifier that is used to
    determine if two items are the same, so action results are cached.
    """
    input_paths = assemble_path_args(*paths)
    for path in input_paths:
        item = current_ws().load(StorePath(path))
        id = item.item_id()
        cprint(
            format_name_and_description(fmt_loc(path), str(id), text_wrap=Wrap.INDENT_ONLY),
            text_wrap=Wrap.NONE,
        )
        PrintHooks.spacer()


@kash_command
def relations(*paths: str) -> None:
    """
    Show the relations for the current selection, including items that are upstream,
    like the items this item is derived from.
    """
    input_paths = assemble_path_args(*paths)

    PrintHooks.spacer()
    for input_path in input_paths:
        item = current_ws().load(StorePath(input_path))
        cprint(f"{fmt_store_path(not_none(item.store_path))}:", style=STYLE_EMPH)
        relations = item.relations.__dict__ if item.relations else {}
        if any(relations.values()):
            cprint(to_yaml_string(relations), text_wrap=Wrap.INDENT_ONLY)
        else:
            cprint("(no relations)", text_wrap=Wrap.INDENT_ONLY)
        PrintHooks.spacer()


def _show_current_params(param_state: ParamState):
    param_values = param_state.get_raw_values()
    print_h2("Current Parameters")
    for key, value in param_values.items():
        cprint(format_name_and_value(key, str(value)))
    cprint()


@kash_command
def set_params(*key_vals: str) -> None:
    """
    Show or set currently set of workspace parameters, which are settings that may be used
    by commands and actions or to override default parameters.

    Run with no args to interactively set parameters.
    """
    ws = current_ws()
    settable_params = GLOBAL_PARAMS

    if key_vals:
        new_key_vals = dict([parse_key_value(arg) for arg in key_vals])

        for key in new_key_vals:
            if key not in settable_params:
                raise InvalidInput(f"Unknown parameter: {key}")

        # Validate enums/valid values for the parameters, if applicable.
        for key, value in new_key_vals.items():
            if value:
                param = settable_params[key]
                param.validate_value(value)

        current_vals = ws.params.get_raw_values()
        new_params = {**current_vals.values, **new_key_vals}

        deletes = [key for key, value in new_params.items() if value is None]
        new_params = remove_values(new_params, deletes)
        ws.params.set(new_params)

    else:
        param = input_param_name(
            "What workspace parameter do you want to set?",
            settable_params,
        )
        if not param:
            raise KeyboardInterrupt()
        cprint()
        print_h3(f"Setting parameter: {param.name}")
        param_value = input_param_value(
            "What value do you want to set it to? (Press enter to unset it, Esc to cancel.)", param
        )

        ws.params.set({param.name: param_value})

        _show_current_params(ws.params)


@kash_command
def list_params(full: bool = False) -> None:
    """
    Show or set currently set of workspace parameters, which are settings that may be used
    by commands and actions or to override default parameters.

    Run with no args to interactively set parameters.
    """
    ws: Workspace = current_ws()
    settable_params = GLOBAL_PARAMS

    with console_pager(use_pager=full):
        print_h2("Available Parameters")
        for param in settable_params.values():
            description: str | None = param.full_description if full else param.description
            cprint(
                format_name_and_description(param.name, description or "", extra_note="(parameter)")
            )
            cprint()

        param_values = ws.params.get_raw_values()
        if not param_values.values:
            print_status("No parameters are set.")
        else:
            _show_current_params(ws.params)


@kash_command
def import_item(
    *files_or_urls: str, type: ItemType | None = None, inplace: bool = False
) -> ShellResult:
    """
    Add a file or URL resource to the workspace as an item, with associated metadata.

    :param inplace: If set and the item is already in the store, reimport the item,
      adding or rewriting metadata frontmatter.
    :param type: Change the item type. Usually items are auto-detected from the file
      format (typically doc or resource), but you can override this with this option.
    """
    if not files_or_urls:
        raise InvalidInput("No files or URLs provided")

    ws = current_ws()
    store_paths = []

    locators = [resolve_locator_arg(r) for r in files_or_urls]
    store_paths = ws.import_items(*locators, as_type=type, reimport=inplace)

    print_status(
        "Imported %s %s:\n%s",
        len(store_paths),
        plural("item", len(store_paths)),
        fmt_lines(store_paths),
    )
    select(*store_paths)

    return ShellResult(show_selection=True)


@kash_command
def fetch_metadata(
    *files_or_urls: str, no_cache: bool = False, refetch: bool = False
) -> ShellResult:
    """
    Fetch metadata for the given URLs or resources. Imports new URLs and saves back
    the fetched metadata for existing resources.

    Skips items that already have a title and description, unless `refetch` is true.
    Skips (with a warning) items that are not URL resources.

    :param use_cache: If true, also save page in content cache.
    """
    if not files_or_urls:
        locators = assemble_store_path_args()
    else:
        locators = [resolve_locator_arg(r) for r in files_or_urls]

    store_paths = []
    for locator in locators:
        try:
            if isinstance(locator, Path):
                raise InvalidInput()
            fetched_item = fetch_url_metadata(locator, use_cache=not no_cache, refetch=refetch)
            store_paths.append(fetched_item.store_path)
        except InvalidInput:
            log.warning("Not a URL or URL resource, will not fetch metadata: %s", fmt_loc(locator))

    if store_paths:
        select(*store_paths)

    return ShellResult(show_selection=True)


@kash_command
def archive(*paths: str) -> None:
    """
    Archive the items at the given path, or the current selection.
    """
    store_paths = assemble_store_path_args(*paths)
    ws = current_ws()
    archived_paths = [ws.archive(store_path) for store_path in store_paths]

    print_status(f"Archived:\n{fmt_lines(fmt_loc(p) for p in archived_paths)}")
    select()


@kash_command
def unarchive(*paths: str) -> None:
    """
    Unarchive the items at the given paths.
    """
    ws = current_ws()
    store_paths = assemble_store_path_args(*paths)
    unarchived_paths = [ws.unarchive(store_path) for store_path in store_paths]

    print_status(f"Unarchived:\n{fmt_lines(fmt_loc(p) for p in unarchived_paths)}")


@kash_command
def clear_archive() -> None:
    """
    Empty the archive to trash.
    """
    ws = current_ws()
    archive_dir = ws.base_dir / ws.dirs.archive_dir
    trash(archive_dir)
    os.makedirs(archive_dir, exist_ok=True)


@kash_command
def suggest_actions(all: bool = False) -> None:
    """
    Suggest actions that can be applied to the current selection.
    """
    applicable_actions(brief=True, all=all)


@kash_command
def applicable_actions(*paths: str, brief: bool = False, all: bool = False) -> None:
    """
    Show the actions that are applicable to the current selection.
    This is a great command to use at any point to see what actions are available!

    :param brief: Show only action names. Otherwise show actions and descriptions.
    :param all: Include actions with no preconditions.
    """
    store_paths = assemble_store_path_args(*paths)
    ws = current_ws()

    actions = get_all_actions_defaults().values()
    applicable_actions = list(
        actions_matching_paths(
            actions,
            ws,
            store_paths,
            include_no_precondition=all,
        )
    )

    if not applicable_actions:
        cprint("No applicable actions for selection.")
        return
    with local_url_formatter(ws.name) as fmt:
        if brief:
            action_names = [action.name for action in applicable_actions]
            cprint(
                format_name_and_value(
                    "Applicable actions",
                    Text.join(
                        Text(", ", style=STYLE_HINT),
                        (fmt.command_link(name) for name in action_names),
                    ),
                ),
            )
        else:
            cprint(
                "Applicable actions for items:\n%s",
                fmt_lines(store_paths),
                text_wrap=Wrap.NONE,
            )
            PrintHooks.hrule()
            for action in applicable_actions:
                precondition_str = (
                    f"(matches precondition {action.precondition})"
                    if action.precondition
                    else "(no precondition)"
                )
                cprint(
                    format_name_and_description(
                        fmt.command_link(action.name),
                        action.description,
                        extra_note=precondition_str,
                    ),
                )
                PrintHooks.hrule()


@kash_command
def preconditions() -> None:
    """
    List all preconditions and if the current selection meets them.
    """

    ws = current_ws()
    selection = ws.selections.current.paths
    if not selection:
        raise InvalidInput("No selection")

    items = [ws.load(item) for item in selection]

    print_status("Precondition check for selection:\n %s", fmt_lines(selection))

    for precondition in get_all_preconditions().values():
        satisfied = all(precondition(item) for item in items)
        emoji = format_success_emoji(satisfied, success_only=True)
        satisfied_str = "satisfied" if satisfied else "not satisfied"
        cprint(
            Text.assemble(emoji, " ", str(precondition), " ", satisfied_str), text_wrap=Wrap.NONE
        )

    PrintHooks.spacer()


@kash_command
def normalize(*paths: str) -> ShellResult:
    """
    Normalize the given items, reformatting files' YAML and text or Markdown according
    to our conventions.
    """
    # TODO: Make a version of this that works outside the workspace on Markdown files,
    # (or another version just called `format` that does this).
    ws = current_ws()
    store_paths = assemble_store_path_args(*paths)

    canon_paths = []
    for store_path in store_paths:
        log.message("Canonicalizing: %s", fmt_loc(store_path))
        for item_store_path in ws.walk_items(store_path):
            try:
                ws.normalize(item_store_path)
            except InvalidInput as e:
                log.warning(
                    "%s Could not canonicalize %s: %s",
                    EMOJI_WARN,
                    fmt_loc(item_store_path),
                    e,
                )
            canon_paths.append(item_store_path)

    # TODO: Also consider implementing duplicate elimination here.

    if len(canon_paths) > 0:
        select(*canon_paths)
    return ShellResult(show_selection=len(canon_paths) > 0)


@kash_command
def reset_ignore_file(append: bool = False) -> None:
    """
    Reset the kash ignore file to the default.
    """
    from kash.utils.file_utils.ignore_files import write_ignore

    ws = current_ws()
    ignore_path = ws.base_dir / ws.dirs.ignore_file
    write_ignore(ignore_path, append=append)

    log.message("Rewrote kash ignore file: %s", fmt_loc(ignore_path))


@kash_command
def ignore_file(pattern: str | None = None) -> None:
    """
    Add a pattern to the kash ignore file, or show the current patterns
    if none is specified.
    """
    from kash.commands.base.show_command import show
    from kash.utils.file_utils.ignore_files import add_to_ignore

    ws = current_ws()
    ignore_path = ws.base_dir / ws.dirs.ignore_file

    if not pattern:
        show(ignore_path)
    else:
        add_to_ignore(ignore_path, [pattern])
