from kash.config.logger import get_logger
from kash.config.settings import global_settings, server_log_file_path
from kash.exec import kash_command
from kash.local_server.local_server import LOCAL_SERVER_NAME
from kash.local_server.local_url_formatters import enable_local_urls
from kash.shell.utils.native_utils import tail_file
from kash.utils.errors import InvalidState

log = get_logger(__name__)


@kash_command
def start_local_server() -> None:
    """
    Start the kash local server. This exposes local info on files and commands so they can be displayed in your terminal, if it supports OSC 8 links.
    Note this is most useful for the Kerm terminal, which shows links as
    tooltips.
    """
    from kash.local_server.local_server import start_local_server

    start_local_server()
    enable_local_urls(True)


@kash_command
def stop_local_server() -> None:
    """
    Stop the kash local server.
    """
    from kash.local_server.local_server import stop_local_server

    stop_local_server()
    enable_local_urls(False)


@kash_command
def restart_local_server() -> None:
    """
    Restart the kash local server.
    """
    from kash.local_server.local_server import restart_local_server

    restart_local_server()


@kash_command
def local_server_logs(follow: bool = False) -> None:
    """
    Show the logs from the kash local server.

    :param follow: Follow the file as it grows.
    """
    log_path = server_log_file_path(LOCAL_SERVER_NAME, global_settings().local_server_port)
    if not log_path.exists():
        raise InvalidState(
            f"Local server log not found (forgot to run `start_local_server`?): {log_path}"
        )
    tail_file(log_path, follow=follow)
