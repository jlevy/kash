import time
from pathlib import Path

from kash.config.logger import get_logger
from kash.config.settings import GLOBAL_LOGS_DIR, global_settings, server_log_file_path
from kash.exec import kash_command
from kash.mcp import mcp_server_routes
from kash.mcp.mcp_server_sse import MCP_LOG_PREFIX, MCP_SERVER_NAME
from kash.shell.output.shell_output import cprint, format_name_and_value, print_h2
from kash.shell.utils.native_utils import tail_file
from kash.utils.errors import InvalidState

log = get_logger(__name__)


@kash_command
def start_mcp_server() -> None:
    """
    Start the MCP server, using all currently known actions marked as MCP tools.
    """
    from kash.mcp.mcp_server_sse import start_mcp_server_sse

    mcp_server_routes.publish_mcp_tools()
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
    Restart the MCP server, republishing all actions marked as MCP tools.
    """
    from kash.mcp.mcp_server_sse import restart_mcp_server_sse

    mcp_server_routes.unpublish_mcp_tools(None)
    mcp_server_routes.publish_mcp_tools()
    restart_mcp_server_sse()


@kash_command
def mcp_logs(follow: bool = False, all: bool = False) -> None:
    """
    Show the logs from the MCP server and CLI proxy process.

    :param follow: Follow the file as it grows.
    :param all: Show all logs, not just the server logs, including Claude Desktop logs if found.
    """
    if all:
        global_log_base = GLOBAL_LOGS_DIR
        claude_log_base = Path("~/Library/Logs/Claude").expanduser()
        log_paths = []
        did_log = False
        while len(log_paths) == 0:
            log_paths = list(global_log_base.glob(f"{MCP_LOG_PREFIX}*.log"))
            claude_logs = list(claude_log_base.glob("mcp*.log"))
            if claude_logs:
                log.message("Found Claude Desktop logs, will also tail them: %s", claude_logs)
                log_paths.extend(claude_logs)
            if log_paths:
                break
            else:
                if not did_log:
                    log.message(
                        "No logs found in %s or %s, waiting for them to appear...",
                        global_log_base,
                        claude_log_base,
                    )
                    did_log = True
                time.sleep(1)
    else:
        server_log_path = server_log_file_path(MCP_SERVER_NAME, global_settings().mcp_server_port)
        if not server_log_path.exists():
            raise InvalidState(
                f"MCP server log not found (forgot to run `start_mcp_server`?): {server_log_path}"
            )
        log_paths = [server_log_path]

    tail_file(*log_paths, follow=follow)


@kash_command
def list_mcp_tools() -> None:
    """
    List published MCP tools.
    """

    tools = mcp_server_routes.get_published_tools()

    if len(tools) == 0:
        cprint("No MCP tools published.")
        return

    print_h2("Published MCP Tools")

    for tool in tools:
        cprint(
            message=format_name_and_value(f"`{tool.name}`", tool.description or "(no description)")
        )
        cprint()


@kash_command
def publish_mcp_tool(*action_names: str) -> None:
    """
    Publish one or more actions as local MCP tools. With no arguments, publish all
    actions marked as MCP tools.
    """
    if not action_names:
        log.message("Publishing all actions marked as MCP tools.")
        mcp_server_routes.publish_mcp_tools()
    else:
        mcp_server_routes.publish_mcp_tools(list(action_names))


@kash_command
def unpublish_mcp_tool(*action_names: str) -> None:
    """
    Un-publish one or more actions as local MCP tools. With no arguments,
    un-publish all published actions.
    """

    if not action_names:
        log.message("Un-publishing all actions marked as MCP tools.")
        mcp_server_routes.unpublish_mcp_tools(None)
    else:
        mcp_server_routes.unpublish_mcp_tools(list(action_names))
