from __future__ import annotations

import asyncio
import pprint
from dataclasses import dataclass

from funlog import log_calls
from mcp.server.lowlevel import Server
from mcp.types import Prompt, Resource, TextContent, Tool
from prettyfmt import fmt_path

from kash.config.capture_output import CapturedOutput, captured_output
from kash.config.logger import get_logger
from kash.config.settings import get_mcp_ws_dir
from kash.exec.action_exec import prepare_action_input, run_action_with_caching
from kash.exec.action_registry import get_all_actions_defaults, look_up_action_class
from kash.model.actions_model import Action, ActionResult, ExecContext
from kash.model.params_model import TypedParamValues
from kash.model.paths_model import StorePath
from kash.utils.common.atomic_var import AtomicVar
from kash.workspaces.workspaces import current_ws, get_ws

log = get_logger(__name__)


# Global list of action names that should be exposed as MCP tools.
_mcp_published_actions: AtomicVar[list[str]] = AtomicVar([])


def publish_mcp_tools(action_names: list[str] | None = None) -> None:
    """
    Add actions to the list of published MCP tools.
    By default, all actions are published.
    """
    global _mcp_published_actions
    if action_names is None:
        actions = get_all_actions_defaults()
        action_names = [name for (name, action) in actions.items() if action.mcp_tool]

    with _mcp_published_actions.updates() as published_actions:
        new_actions = set(action_names).difference(published_actions)
        published_actions.extend(new_actions)
        log.message(
            "Published %s MCP tools (total now %s): %s",
            len(new_actions),
            len(published_actions),
            new_actions,
        )


def unpublish_mcp_tools(action_names: list[str] | None) -> None:
    """
    Unpublish one or more actions as local MCP tools.
    """
    global _mcp_published_actions
    with _mcp_published_actions.updates() as published_actions:
        if action_names is None:
            published_actions[:] = []
            log.message("Unpublished all MCP tools")
        else:
            published_actions[:] = [name for name in published_actions if name not in action_names]
            log.message(
                "Unpublished %s MCP tools (total now %s): %s",
                len(action_names),
                len(published_actions),
                action_names,
            )


def tool_for_action(action: Action) -> Tool:
    """
    Create a tool for an action.
    """
    return Tool(
        name=action.name,
        description=action.description,
        inputSchema=action.tool_json_schema(),
    )


@log_calls(level="info")
def get_published_tools() -> list[Tool]:
    """
    Get all tools that are published as MCP tools.
    """
    try:
        with captured_output():
            actions = get_all_actions_defaults()
            tools = [
                tool_for_action(actions[name])
                for name in _mcp_published_actions.copy()
                if name in actions
            ]
            if len(tools) > 0:
                log.info(
                    "Offering %s tools:\n%s",
                    len(tools),
                    "\n".join(pprint.pformat(t.inputSchema) for t in tools),
                )
            else:
                log.warning("No tools to offer! Missing import?")
            return tools
    except Exception:
        log.exception("Error listing tools")
        return []


@dataclass(frozen=True)
class ToolResult:
    """
    Result of an MCP tool call.
    """

    action: Action
    captured_output: CapturedOutput
    action_result: ActionResult
    result_store_paths: list[StorePath]
    error: Exception | None = None

    @property
    def output_summary(self) -> str:
        """
        Return a message about the results of the action.
        """
        if self.result_store_paths:
            message = (
                f"This tool `{self.action.name}` created the following output files:\n\n"
                + "\n".join(fmt_path(p) for p in self.result_store_paths)
            )
        else:
            message = (
                f"The tool `{self.action.name}` did not create any output files.\n\n"
                + self.check_logs_message
            )
            log.warning("%s", message)

        return message

    @property
    def output_content(self) -> str:
        """
        Return the content of the output files.
        """
        if len(self.action_result.items) > 0:
            path = self.result_store_paths[0]
            body = self.action_result.items[0].body or "(empty)"
            extra_msg = ""
            if len(self.action_result.items) > 1:
                extra_msg = (
                    f"Omitting the contents of the other {len(self.action_result.items) - 1} items."
                )
            return (
                f"The contents of the output file `{fmt_path(path)}` is below. {extra_msg}\n\n"
                + body
            )
        else:
            return ""

    @property
    def check_logs_message(self) -> str:
        """
        Return a message about the logs from this tool call.
        """
        # TODO: Add more info on how to find the logs.
        return "Check kash logs for details."

    def formatted_for_client(self) -> list[TextContent]:
        """
        Convert the tool result to content for the client LLM.
        """
        if self.error:
            return [
                TextContent(
                    text=f"The tool `{self.action.name}` had an error: {self.error}.\n\n"
                    + self.check_logs_message,
                    type="text",
                )
            ]
        else:
            if self.result_store_paths:
                chat_result = f"The result of this action is: {', '.join(fmt_path(p) for p in self.result_store_paths)}"
            else:
                log.warning(
                    "No result from tool call to action `%s`: %s",
                    self.action.name,
                    self.action_result,
                )
                chat_result = None

            if not chat_result:
                chat_result = "No result. Check kash logs for details."

            return [
                TextContent(
                    text=f"{self.output_summary}\n\n"
                    f"{self.output_content}\n\n"
                    f"Additional logs from this tool call:\n\n```{self.captured_output.logs}```\n",
                    type="text",
                ),
            ]


@log_calls(level="info")
def run_mcp_tool(action_name: str, arguments: dict) -> list[TextContent]:
    """
    Run the action as a tool.
    """
    try:
        with captured_output() as capture:
            # XXX For now, unless the user has overridden the MCP workspace, we use the
            # current workspace, which could be changed by the user by changing working
            # directories. Maybe confusing?
            explicit_mcp_ws = get_mcp_ws_dir()
            ws = get_ws(explicit_mcp_ws) if explicit_mcp_ws else current_ws()

            with ws:
                action_cls = look_up_action_class(action_name)

                # Extract items array and remaining params from arguments.
                input_items = arguments.pop("items", [])

                # Create typed param values directly from schema-validated inputs, then
                # create an action instance with fully set parameters.
                param_values = TypedParamValues.create(arguments, action_cls.create(None).params)
                action = action_cls.create(param_values)

                # Create execution context and assemble action input.
                context = ExecContext(
                    action=action,
                    workspace_dir=ws.base_dir,
                    # Enabling rerun always for now, seems good for tools.
                    rerun=True,
                    # Keeping all transient files for now, but maybe make transient?
                    override_state=None,
                )
                action_input = prepare_action_input(*input_items)

                result, result_store_paths, _archived_store_paths = run_action_with_caching(
                    context=context, action_input=action_input
                )

        # Return final result, formatted for the LLM to understand.
        return ToolResult(
            action=action,
            captured_output=capture.output,
            action_result=result,
            result_store_paths=result_store_paths,
            error=None,
        ).formatted_for_client()

    except Exception as e:
        log.exception("Error running mcp tool")
        return [
            TextContent(
                text=f"Call to tool `{action_name}` had an error: {e}.\n\n"
                + "Check kash logs for details.",
                type="text",
            )
        ]


def create_base_server() -> Server:
    """
    Creates the base MCP server with tool definitions.
    """
    app = Server("kash-mcp-server")

    @app.list_tools()
    async def list_tools() -> list[Tool]:
        log.info("Handling list_tools request")
        return await asyncio.to_thread(get_published_tools)

    # We don't support prompts/resources yet but implementing these to avoid
    # having MCP clients log (possibly confusing) errors.

    @app.list_prompts()
    async def list_prompts() -> list[Prompt]:
        log.info("Handling list_prompts request")
        # Nothing implemented yet!
        return []

    @app.list_resources()
    async def list_resources() -> list[Resource]:
        log.info("Handling list_resources request")
        # Nothing implemented yet!
        return []

    @app.call_tool()
    async def handle_tool(name: str, arguments: dict) -> list[TextContent]:
        try:
            if name not in _mcp_published_actions.copy():
                log.error(f"Unknown tool requested: {name}")
                raise ValueError(f"Unknown tool: {name}")

            log.info(f"Handling tool call: {name} with arguments: {arguments}")
            return await asyncio.to_thread(run_mcp_tool, name, arguments)
        except Exception as e:
            log.exception(f"Error handling tool call {name}")
            return [
                TextContent(
                    text=f"Error executing tool {name}: {e}",
                    type="text",
                )
            ]

    return app
