from kash.config.logger import get_logger
from kash.config.settings import global_settings
from kash.exec import kash_command
from kash.local_server.local_url_formatters import enable_local_urls
from kash.shell.utils.native_utils import tail_file
from kash.utils.errors import InvalidState

log = get_logger(__name__)


@kash_command
def start_ui_server() -> None:
    """
    Start the kash local ui server. This exposes local info on files and commands so
    they can be displayed in your terminal, if it supports OSC 8 links.
    Note this is most useful for the Kerm terminal, which shows links as
    tooltips.
    """
    from kash.local_server.local_server import start_ui_server

    start_ui_server()
    enable_local_urls(True)


@kash_command
def stop_ui_server() -> None:
    """
    Stop the kash local server.
    """
    from kash.local_server.local_server import stop_ui_server

    stop_ui_server()
    enable_local_urls(False)


@kash_command
def restart_ui_server() -> None:
    """
    Restart the kash local server.
    """
    from kash.local_server.local_server import restart_ui_server

    restart_ui_server()


@kash_command
def local_server_logs(follow: bool = False) -> None:
    """
    Show the logs from the kash local (UI and MCP) servers.

    :param follow: Follow the file as it grows.
    """
    log_path = global_settings().local_server_log_path
    if not log_path.exists():
        raise InvalidState(
            f"Local ui server log not found (forgot to run `start_ui_server`?): {log_path}"
        )
    tail_file(log_path, follow=follow)
