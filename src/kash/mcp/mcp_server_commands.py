from kash.config.logger import get_logger
from kash.config.settings import global_settings, server_log_file_path
from kash.exec import kash_command
from kash.mcp.mcp_server_routes import publish_mcp_tools
from kash.mcp.mcp_server_sse import MCP_SERVER_NAME
from kash.shell_tools.native_tools import tail_file

log = get_logger(__name__)


@kash_command
def start_mcp_server() -> None:
    """
    Start the MCP server.
    """
    from kash.mcp.mcp_server_sse import start_mcp_server_sse

    start_mcp_server_sse()


@kash_command
def stop_mcp_server() -> None:
    """
    Stop the MCP server.
    """
    from kash.mcp.mcp_server_sse import stop_mcp_server_sse

    stop_mcp_server_sse()


@kash_command
def restart_mcp_server() -> None:
    """
    Restart the MCP server.
    """
    from kash.mcp.mcp_server_sse import restart_mcp_server_sse

    restart_mcp_server_sse()


@kash_command
def mcp_server_logs(follow: bool = False) -> None:
    """
    Show the logs from the MCP server.

    :param follow: Follow the file as it grows.
    """
    log_path = server_log_file_path(MCP_SERVER_NAME, global_settings().mcp_server_port)
    tail_file(log_path, follow=follow)


@kash_command
def publish_mcp_tool(*action_names: str) -> None:
    """
    Publish one or more actions as local MCP tools.
    """
    publish_mcp_tools(list(action_names))
