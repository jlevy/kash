"""
Standalone action runner for kash.

Provides `kash_init()` and `kash_run()` to execute any kash action as a
Python library call without the interactive shell.

Example usage::

    from kash.run import kash_init, kash_run

    kash_init()
    result = kash_run("strip_html", ["https://example.com/page.html"])
    print(result.items[0].body)

Or using the convenience `kash_run()` which auto-initializes::

    from kash.run import kash_run

    result = kash_run("strip_html", ["https://example.com/page.html"])

With an explicit workspace::

    from kash.run import kash_run

    result = kash_run(
        "summarize_as_bullets",
        ["https://example.com"],
        workspace_dir="/tmp/my_workspace",
    )
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from kash.config.logger import get_logger
from kash.exec.action_exec import run_action_operation, save_action_result
from kash.exec.action_registry import look_up_action_class
from kash.model.actions_model import Action, ActionInput, ActionResult, ExecContext
from kash.model.exec_model import ActionContext, RuntimeSettings
from kash.model.items_model import Item, ItemType
from kash.model.operations_model import Input, Operation
from kash.model.params_model import ALL_COMMON_PARAMS, RawParamValue, RawParamValues
from kash.utils.common.url import Url, is_url
from kash.utils.errors import InvalidInput
from kash.utils.file_utils.file_formats_model import Format

log = get_logger(__name__)

_initialized = False


def kash_init(
    *,
    workspace_dir: Path | str | None = None,
    log_level: str = "warning",
    quiet: bool = True,
) -> None:
    """
    One-time lightweight initialization for library use. No xonsh or shell needed.

    Sets up logging, loads environment variables and API keys, and optionally
    configures a default workspace directory.

    Idempotent: safe to call multiple times.
    """
    global _initialized
    if _initialized:
        return
    _initialized = True

    from kash.config.setup import kash_setup

    kash_setup(
        rich_logging=False,
        log_level=log_level,
        console_log_level="error" if quiet else "warning",
        console_quiet=quiet,
        kash_ws_root=Path(workspace_dir) if workspace_dir else None,
    )


def kash_run(
    action_name: str,
    inputs: list[str | Item] | None = None,
    *,
    params: dict[str, RawParamValue] | None = None,
    workspace_dir: Path | str | None = None,
    rerun: bool = False,
    no_format: bool = False,
    save_results: bool = True,
) -> ActionResult:
    """
    Run a kash action by name and return the structured result.

    This is the main entry point for using kash as a library. Does not require
    the interactive shell or xonsh.

    Args:
        action_name: Name of the registered action (e.g. "strip_html",
            "summarize_as_bullets").
        inputs: List of input items. Each can be a URL string, a file path string,
            or an existing Item object. If None or empty, runs the action with no inputs.
        params: Optional action parameters as key-value pairs
            (e.g. {"model": "claude-sonnet-4-20250514"}).
        workspace_dir: Workspace directory for storing results. If not provided,
            uses a temporary directory.
        rerun: If True, force re-execution even if cached results exist.
        no_format: If True, skip Markdown formatting normalization on output.
        save_results: If True (default), save result items to the workspace.

    Returns:
        ActionResult containing the output Items.

    Raises:
        InvalidInput: If the action name is not found or inputs are invalid.
    """
    # Auto-initialize if not done yet.
    kash_init()

    # Resolve workspace.
    ws_path = _resolve_workspace_dir(workspace_dir)

    # Look up the action class and instantiate with params.
    action_cls = look_up_action_class(action_name)
    if params:
        raw_params = RawParamValues(values=params)
        # Get declared params from an unparameterized instance, then parse raw to typed.
        declared_params = {p.name: p for p in action_cls.create(None).params}
        typed_params = raw_params.parse_all({**ALL_COMMON_PARAMS, **declared_params})
    else:
        typed_params = None
    action = action_cls.create(typed_params)

    # Build ActionInput from the provided inputs.
    action_input = _build_action_input(inputs, ws_path)

    # Build RuntimeSettings and ExecContext.
    settings = RuntimeSettings(
        workspace_dir=ws_path,
        rerun=rerun,
        no_format=no_format,
        sync_to_s3=False,  # Library use: no auto S3 sync.
    )
    exec_context = ExecContext(action, settings)

    # Validate and build operation.
    operation = _validate_and_build_operation(exec_context, action, action_input)

    # Build full ActionContext.
    context = ActionContext(
        exec_context=exec_context,
        operation=operation,
        action_input=action_input,
    )

    try:
        action_input.set_context(context)

        # Run the action.
        result = run_action_operation(context, action_input, operation)

        # Save results to workspace if requested.
        if save_results:
            ws = settings.workspace
            save_action_result(ws, result, action_input, no_format=no_format)

    finally:
        action_input.clear_context()

    return result


def _resolve_workspace_dir(workspace_dir: Path | str | None) -> Path:
    """
    Resolve the workspace directory. If not provided, create a temporary one.
    """
    if workspace_dir:
        ws_path = Path(workspace_dir).expanduser().absolute()
        ws_path.mkdir(parents=True, exist_ok=True)
        return ws_path

    # Try to use existing workspace from current directory.
    try:
        from kash.workspaces.workspace_dirs import enclosing_ws_dir

        enclosing = enclosing_ws_dir()
        if enclosing:
            return enclosing
    except Exception:
        pass

    # Fall back to a temporary workspace.
    tmp_dir = Path(tempfile.mkdtemp(prefix="kash_run_"))
    log.info("Using temporary workspace: %s", tmp_dir)
    return tmp_dir


def _build_action_input(
    inputs: list[str | Item] | None,
    _ws_path: Path,
) -> ActionInput:
    """
    Build ActionInput from a list of strings (URLs or paths) and/or Item objects.
    """
    if not inputs:
        return ActionInput.empty()

    items: list[Item] = []
    for inp in inputs:
        if isinstance(inp, Item):
            items.append(inp)
        elif isinstance(inp, str):
            if is_url(inp):
                item = Item(
                    url=Url(inp),
                    type=ItemType.resource,
                    title=inp,
                    format=Format.url,
                )
            else:
                # Treat as a file path.
                path = Path(inp).expanduser().absolute()
                if path.is_file():
                    body = path.read_text(errors="replace")
                    item = Item(
                        type=ItemType.doc,
                        title=path.name,
                        body=body,
                        external_path=str(path),
                    )
                else:
                    raise InvalidInput(f"Input file not found: {inp}")
            items.append(item)
        else:
            raise InvalidInput(f"Invalid input type: {type(inp)}")

    return ActionInput(items=items)


def _validate_and_build_operation(
    exec_context: ExecContext,
    action: Action,
    action_input: ActionInput,
) -> Operation:
    """
    Validate the action input and build an Operation describing what will happen.
    Simplified version of the full validation in action_exec.py.
    """
    input_items = action_input.items

    # Validate arg counts and params.
    action.validate_args(len(input_items))
    action.validate_params_present()
    action.validate_precondition(action_input)

    # Build operation record.
    op_inputs = [
        Input(path=None, source_info=item.url or item.title or "input") for item in input_items
    ]

    options = {**action.param_value_summary(), **exec_context.settings.non_default_options}
    return Operation(action.name, op_inputs, options)
