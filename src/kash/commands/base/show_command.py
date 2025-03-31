from kash.config.logger import get_logger
from kash.config.text_styles import STYLE_HINT
from kash.exec import assemble_path_args, kash_command
from kash.model.paths_model import StorePath
from kash.shell.output.shell_output import cprint
from kash.shell.utils.native_utils import ViewMode, terminal_show_image, view_file_native
from kash.utils.errors import InvalidInput, InvalidState
from kash.web_content.file_cache_utils import cache_file
from kash.workspaces import current_ws

log = get_logger(__name__)


@kash_command
def show(
    path: str | None = None,
    console: bool = False,
    native: bool = False,
    thumbnail: bool = False,
    browser: bool = False,
) -> None:
    """
    Show the contents of a file if one is given, or the first file if multiple files
    are selected. Will try to use native apps or web browser to display the file if
    appropriate, and otherwise display the file in the console.

    Will use `bat` if available to show files in the console, including syntax
    highlighting and git diffs.

    :param console: Force display to console (not browser or native apps).
    :param native: Force display with a native app (depending on your system configuration).
    :param thumbnail: If there is a thumbnail image, show it too.
    :param browser: Force display with your default web browser.
    """
    view_mode = (
        ViewMode.console
        if console
        else ViewMode.browser
        if browser
        else ViewMode.native
        if native
        else ViewMode.auto
    )
    try:
        input_paths = assemble_path_args(path)
        input_path = input_paths[0]

        if isinstance(input_path, StorePath):
            ws = current_ws()
            if input_path.is_file():
                # Optionally, if we can inline display the image (like in kitty) above the text representation, do that.
                item = ws.load(input_path)
                if thumbnail and item.thumbnail_url:
                    try:
                        local_path, _was_cached = cache_file(item.thumbnail_url)
                        terminal_show_image(local_path)
                    except Exception as e:
                        log.info("Had trouble showing thumbnail image (will skip): %s", e)
                        cprint(f"[Image: {item.thumbnail_url}]", style=STYLE_HINT)

            view_file_native(ws.base_dir / input_path, view_mode=view_mode)
        else:
            view_file_native(input_path, view_mode=view_mode)
    except (InvalidInput, InvalidState):
        if path:
            # If path is absolute or we couldbn't get a selection, just show the file.
            view_file_native(path, view_mode=view_mode)
        else:
            raise InvalidInput("No selection")
