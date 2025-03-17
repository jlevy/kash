from kash.commands.base.basic_file_commands import trash
from kash.config.logger import get_logger
from kash.exec import kash_command
from kash.shell.output.shell_output import PrintHooks, cprint, format_name_and_value, print_h2

log = get_logger(__name__)


@kash_command
def global_settings() -> None:
    """
    Show all global kash settings.
    """
    from kash.config.settings import global_settings

    settings = global_settings()
    print_h2("Global Settings")
    for field, value in settings.__dict__.items():
        cprint(format_name_and_value(field, str(value)))
    PrintHooks.spacer()


@kash_command
def clear_global_cache(media: bool = False, content: bool = False) -> None:
    """
    Clear the global media and content caches. By default clears both caches.

    :param media: Clear the media cache only.
    :param content: Clear the content cache only.
    """
    from kash.config.settings import global_settings

    if not media and not content:
        media = True
        content = True

    if media and global_settings().media_cache_dir.exists():
        trash(global_settings().media_cache_dir)

    if content and global_settings().content_cache_dir.exists():
        trash(global_settings().content_cache_dir)
