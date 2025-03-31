import inspect
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from textwrap import dedent
from typing import (
    Any,
    Concatenate,
    ParamSpec,
    TypeAlias,
    TypeVar,
    cast,
)

from funlog import format_func_call
from prettyfmt import fmt_lines
from pydantic.dataclasses import dataclass as pydantic_dataclass
from pydantic.dataclasses import is_pydantic_dataclass
from typing_extensions import override

from kash.config.logger import get_logger
from kash.exec.action_exec import run_action_with_caching
from kash.exec.action_registry import register_action_class
from kash.exec_model.args_model import ONE_ARG, ArgCount, ArgType
from kash.model.actions_model import (
    Action,
    ActionInput,
    ActionResult,
    ExecContext,
    LLMOptions,
    ParamSource,
    TitleTemplate,
)
from kash.model.items_model import Item, ItemType, State
from kash.model.params_model import Param, ParamDeclarations, TypedParamValues
from kash.model.preconditions_model import Precondition
from kash.utils.common.function_inspect import FuncParam, inspect_function_params
from kash.utils.errors import InvalidDefinition
from kash.workspaces.workspaces import current_ws

log = get_logger(__name__)


P = ParamSpec("P")


ActionFunction: TypeAlias = Callable[Concatenate[ActionInput, P], ActionResult]
"""
Signature of a function that can be registered as an action via `@kash_action`.
"""

SimpleActionFunction: TypeAlias = Callable[Concatenate[Item, P], Item]
"""
Signature of a simplified action function that processes and returns a single `Item`.
"""

AnyActionFunction: TypeAlias = ActionFunction | SimpleActionFunction

# TODO: Add a NoInputActionFunction convenience type so you can annotate
# functions that take no input, like `write_instructions`.

AF = TypeVar("AF", bound=AnyActionFunction)


def _source_path(obj: Any) -> Path | None:
    if hasattr(obj, "__source_path__"):
        return obj.__source_path__

    try:
        if source_file := inspect.getsourcefile(obj):
            return Path(source_file).resolve()
    except TypeError:
        pass
    return None


A = TypeVar("A", bound=Action)
T = TypeVar("T")
R = TypeVar("R")


def kash_action_class(cls: type[A]) -> type[A]:
    """
    Class decorator to register an action. This also ensures that the action is
    a Pydantic dataclass and records the source path in `__source_path__`.
    """

    # Validate the class.
    if not issubclass(cls, Action):
        raise TypeError(f"Registered action class {cls.__name__} must be a subclass of Action")
    if not getattr(cls, "name", None):
        raise TypeError(f"Registered action class {cls.__name__} must have a `name` attribute")

    # Apply Pydantic's @dataclass decorator if not already a Pydantic dataclass.
    if not is_pydantic_dataclass(cls):
        pyd_cls = cast(type[A], pydantic_dataclass(cls))
    else:
        pyd_cls = cast(type[A], cls)

    pyd_cls.__source_path__ = _source_path(cls)  # pyright: ignore

    register_action_class(pyd_cls)

    return pyd_cls


def _register_dynamic_action(
    action_cls: type[A], action_name: str, action_description: str, source_path: Path | None
) -> type[A]:
    # Set class fields for name and description for convenience.
    action_cls.name = action_name
    action_cls.description = action_description

    action_cls.__name__ = f"{action_name.title().replace('_', '')}Action"
    action_cls.__qualname__ = action_cls.__name__
    action_cls.__module__ = action_cls.__module__
    action_cls.__doc__ = action_description

    # Register the new action class.
    pyd_cls = kash_action_class(action_cls)

    pyd_cls.__source_path__ = source_path  # pyright: ignore
    return pyd_cls


def _merge_param_declarations(
    action_name: str,
    params: ParamDeclarations,
    func_params: list[FuncParam],
    param_start_pos: int = 1,
) -> tuple[ParamDeclarations, set[str]]:
    """
    Merge param declarations from the `@kash_action` decorator with the formal parameters
    of the decorated function.
    """

    # Get the formal params and their defaults.
    if any(fp.is_varargs for fp in func_params):
        raise InvalidDefinition(
            "Varargs parameters are not supported for `@kash_action` decorator "
            f"on action `{action_name}`"
        )
    # Option to skip the first positional parameter (the action input).
    func_params = func_params[param_start_pos:]

    # The params declared for this action will need to reflect the params declared as
    # args to the function, merging in info from any params declared in the decorator,
    # and finally if needed, filling in any missing defaults from global common param values.

    # First, the declared params must all appear as function arguments.
    merged_params = {param.name: param for param in params}
    if any(fp.name not in merged_params for fp in func_params):
        raise InvalidDefinition(
            f"Action function `{action_name}` declared params but not all appear "
            f"as function parameters: params={params}, func_params={func_params}"
        )

    # Now assemble the param declarations with updated defaults.
    func_params_with_defaults = set()
    for fp in func_params:
        param_info = merged_params.get(fp.name)
        if param_info:
            # This function parameter matches a declared param.
            if fp.has_default:
                merged_params[fp.name] = merged_params[fp.name].with_default(fp.default)
                func_params_with_defaults.add(fp.name)
        else:
            log.warning(
                "In action `%s`, function parameter `%s` does not appear in the `params` "
                "declaration of the `register_action` decorator; add it for better docs",
                action_name,
                fp.name,
            )
            merged_params[fp.name] = Param(
                name=fp.name,
                description=None,
                type=fp.type or str,
                default_value=fp.default if fp.has_default else None,
                is_explicit=not fp.has_default,
            )

    return tuple(merged_params.values()), func_params_with_defaults


def _set_param_values(params: ParamDeclarations, fp_overrides: set[str], action: Action):
    # Set all parameters, noting which ones were overridden by a function default.
    for param in params:
        source = (
            ParamSource.function_default
            if param.name in fp_overrides
            else ParamSource.global_default
        )
        action.set_param(param.name, param.default_value, source)


def kash_action(
    name: str | None = None,
    description: str | None = None,
    cacheable: bool = True,
    precondition: Precondition = Precondition.always,
    arg_type: ArgType = ArgType.Locator,
    expected_args: ArgCount = ONE_ARG,
    output_type: ItemType = ItemType.doc,
    expected_outputs: ArgCount = ONE_ARG,
    params: ParamDeclarations = (),
    run_per_item: bool | None = None,
    uses_selection: bool = True,
    interactive_input: bool = False,
    mcp_tool: bool = False,
    title_template: TitleTemplate = TitleTemplate("{title}"),
    llm_options: LLMOptions = LLMOptions(),
    override_state: State | None = None,
    rerun: bool = False,
) -> Callable[[AF], AF]:
    """
    A function decorator to create and register an action. The annotated function must
    be either:

    - a "regular" action function with an `ActionInput` as its first formal parameter
      and returning an `ActionResult`

    - a "simple" action function with a single `Item` as its first formal parameter
      and returning a single `Item`

    It may optionally have a `context` keyword parameter of type `ExecContext` to
    get the current execution context.

    The `name` and `description` usually should be omitted as they are by default inferred
    from the function name and docstring.

    Parameters are inferred from the function's other formal parameters. You should
    declare their details in `params` using the same names as the function parameters.

    See `Action` for more docs.
    """

    def decorator(orig_func: AF) -> AF:
        if hasattr(orig_func, "__action_class__"):
            log.warning(
                "Function `%s` is already decorated with `@kash_action`", orig_func.__name__
            )
            return orig_func

        # Inspect and sanity check the formal params.
        func_params = inspect_function_params(orig_func)
        if len(func_params) == 0 or func_params[0].type not in (ActionInput, Item):
            raise InvalidDefinition(
                f"Decorator `@kash_action` requires exactly one positional parameter, "
                f"`input` of type `ActionInput` or `Item` on function `{orig_func.__name__}` but "
                f"got params: {func_params}"
            )
        if any(fp.is_positional for fp in func_params[1:]):
            raise InvalidDefinition(
                "Decorator `@kash_action` requires all parameters after the first positional "
                f"parameter to be keyword parameters on function `{orig_func.__name__}` but "
                f"got params: {func_params}"
            )

        # Remove the context parameter if present.
        context_param = next((fp for fp in func_params if fp.name == "context"), None)
        if context_param:
            func_params.remove(context_param)
        if context_param and context_param.is_positional:
            raise InvalidDefinition(
                "Decorator `@kash_action` requires the `context` parameter to be a keyword "
                "parameter, not positional, on function `{func.__name__}`"
            )

        # If the original function is a simple action function (processes a single item),
        # wrap it to convert to an ActionFunction.
        is_simple_func = func_params[0].type == Item
        action_func: ActionFunction
        if is_simple_func:
            simple_func = cast(SimpleActionFunction, orig_func)

            @wraps(simple_func)
            def converted_func(
                input: ActionInput, *args: P.args, **kwargs: P.kwargs
            ) -> ActionResult:
                result_item = simple_func(input.items[0], *args, **kwargs)
                return ActionResult(items=[result_item])

            action_func = converted_func
        else:
            action_func = cast(ActionFunction, orig_func)

        # Honor an explicit run_per_item, but otherwise infer it from is_simple_func.
        updated_run_per_item = run_per_item if run_per_item is not None else is_simple_func

        # Merge the declared decorator params with the formal function parameters.
        action_name = name or action_func.__name__
        action_description = description or dedent(action_func.__doc__ or "").strip()
        merged_params, fp_overrides = _merge_param_declarations(action_name, params, func_params)

        # Now declare the new action class, overriding fields, params, and run().
        class FuncAction(Action):
            @override
            def __post_init__(self):
                # We do this dynamically post-init since we want dynamic (not static class)
                # scoping.
                self.name = action_name
                self.description = action_description
                # Extra overrides for simple (per-item) actions, which must always have
                # one input and one output.
                self.expected_args = ONE_ARG if is_simple_func else expected_args
                self.expected_outputs = ONE_ARG if is_simple_func else expected_outputs
                self.params = merged_params
                self.run_per_item = updated_run_per_item

                self.cacheable = cacheable
                self.precondition = precondition
                self.arg_type = arg_type
                self.uses_selection = uses_selection
                self.output_type = output_type
                self.interactive_input = interactive_input
                self.mcp_tool = mcp_tool
                self.title_template = title_template
                self.llm_options = llm_options

                _set_param_values(self.params, fp_overrides, self)
                super().__post_init__()

            @override
            def run(self, input: ActionInput, context: ExecContext) -> ActionResult:
                # Map the final, current actions param values back to the function parameters.
                pos_args: list[Any] = []
                kw_args: dict[str, Any] = {}
                if context_param:
                    kw_args["context"] = context
                for fp in func_params[1:]:
                    if fp.is_positional:
                        pos_args.append(self.get_param(fp.name))
                    else:
                        kw_args[fp.name] = self.get_param(fp.name)

                log.info("Action function param declarations:\n%s", fmt_lines(self.params))
                log.info("Action function param values:\n%s", self.param_value_summary_str())

                log.message(
                    "Action function call:\n%s",
                    fmt_lines([format_func_call(self.name, [input] + pos_args, kw_args)]),
                )
                # Call the underlying function with the mapped arg values.
                return action_func(input, *pos_args, **kw_args)  # pyright: ignore

        _register_dynamic_action(
            FuncAction, action_name, action_description, _source_path(orig_func)
        )

        # Define the modified function for use when called directly in Python.
        @wraps(action_func)
        def wrapped_func(
            action_input: ActionInput, *args: P.args, **kwargs: P.kwargs
        ) -> ActionResult:
            # We'll map the Python kwargs to kash param values then pass that to the action,
            # which will map them back to the original function. Kind of convoluted but this
            # way the logic is identical for plain Python invocation and general action execution.
            param_values: dict[str, Any] = {}
            if len(args) > 0:
                raise ValueError(
                    f"Unexpected positional arguments: {args} on function `{orig_func.__name__}`"
                )

            for name, value in kwargs.items():
                param_values[name] = value
            log.info(
                "Mapped function args to params:\n%s",
                fmt_lines([kwargs, param_values]),
            )

            # Create the new action with all explicit param values.
            action = FuncAction.create(TypedParamValues.create(param_values, merged_params))

            # Set up the execution context.
            # Get the context if it is provided (unlikely when used directly) or otherwise
            # use the current workspace.
            provided_context = cast(ExecContext | None, kwargs.pop("context", None))
            if provided_context:
                context = provided_context
            else:
                context = ExecContext(
                    action, current_ws().base_dir, rerun=rerun, override_state=override_state
                )

            # Run the action.
            result, _, _ = run_action_with_caching(context, action_input, rerun=rerun)

            return result

        if is_simple_func:
            # Need to convert back to a SimpleActionFunction.
            @wraps(wrapped_func)
            def simple_action_func(item: Item, *args: P.args, **kwargs: P.kwargs) -> Item:
                result = wrapped_func(ActionInput(items=[item]), *args, **kwargs)  # pyright: ignore
                if len(result.items) != 1:
                    raise ValueError(
                        f"Expected exactly one item in result of simple action function "
                        f"`{orig_func.__name__}` but got {len(result.items)} items: {result.items}"
                    )
                return result.items[0]

            final_func = cast(AF, simple_action_func)  # pyright: ignore
        else:
            final_func = cast(AF, wrapped_func)  # pyright: ignore

        # Usual __name__ etc already set by @wraps but we also set our own meta fields.
        final_func.__action_class__ = FuncAction  # pyright: ignore
        final_func.__source_path__ = _source_path(orig_func)  # pyright: ignore

        return final_func

    return decorator
