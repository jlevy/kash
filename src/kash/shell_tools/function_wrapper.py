from enum import Enum
from functools import wraps
from typing import Any, Callable, cast, Dict, List, Mapping, Optional, Tuple, TypeVar

from kash.commands.help_commands import help_commands
from kash.config.logger import get_logger
from kash.errors import InvalidCommand
from kash.exec.command_registry import CommandFunction
from kash.help.command_help import print_command_function_help
from kash.util.function_inspect import FuncParam, inspect_function_params
from kash.util.parse_shell_args import parse_shell_args

log = get_logger(__name__)


def _map_positional(
    pos_args: List[str], pos_params: List[FuncParam], kw_params: List[FuncParam]
) -> Tuple[List[Any], int]:
    """
    Map parsed positional arguments to function parameters, ensuring the number of
    arguments matches and converting types.
    """
    pos_values = []
    i = 0
    keywords_consumed = 0

    for param in pos_params:
        param_type = param.type or str
        if param.is_varargs:
            pos_values.extend([param_type(arg) for arg in pos_args[i:]])
            return pos_values, 0  # All remaining args are consumed, so we can return early.
        elif i < len(pos_args):
            pos_values.append(param_type(pos_args[i]))
            i += 1
        else:
            raise InvalidCommand(f"Missing positional argument: {param.name}")

    # If there are remaining positional arguments, they will go toward keyword arguments.
    for param in kw_params:
        param_type = param.type or str
        if not param.is_varargs and i < len(pos_args):
            pos_values.append(param_type(pos_args[i]))
            i += 1
            keywords_consumed += 1

    if i < len(pos_args):
        raise InvalidCommand(
            f"Too many arguments provided (expected {len(pos_params)}, got {len(pos_args)}): {pos_args}"
        )

    return pos_values, keywords_consumed


def _map_keyword(kw_args: Mapping[str, str | bool], kw_params: List[FuncParam]) -> Dict[str, Any]:
    """
    Map parsed keyword arguments to function parameters, converting types and handling var
    keyword arguments.
    """

    kw_values = {param.name: param.default for param in kw_params if not param.is_varargs}
    var_kw_values = {}
    var_kw_param = None

    # Find the var keyword argument (**kwargs), if any.
    var_kw_param = next((param for param in kw_params if param.is_varargs), None)

    # Map the keyword arguments to the function parameters.
    for key, value in kw_args.items():
        matching_param = next((param for param in kw_params if param.name == key), None)
        if matching_param:
            matching_param_type = matching_param.type or str

            if isinstance(value, bool) and not issubclass(matching_param_type, bool):
                raise InvalidCommand(f"Option `--{key}` expects a value")
            if not isinstance(value, bool) and issubclass(matching_param_type, bool):
                raise InvalidCommand(f"Option `--{key}` is boolean and does not take a value")

            try:
                kw_values[key] = matching_param_type(value)  # Convert value to type.
            except Exception as e:
                valid_values = ""
                if isinstance(matching_param.type, type) and issubclass(matching_param.type, Enum):
                    valid_values = f" (valid values are: {', '.join('`' + v.name + '`' for v in matching_param.type)})"
                raise InvalidCommand(
                    f"Invalid value for option `{key}`: {value}{valid_values}"
                ) from e
        elif var_kw_param:
            var_kw_values[key] = value
        else:
            raise InvalidCommand(f"Unknown option `--{key}`")

    if var_kw_param:
        kw_values.update(var_kw_values)

    return kw_values


R = TypeVar("R")


def wrap_for_shell_args(func: Callable[..., R]) -> Callable[[List[str]], Optional[R]]:
    """
    Wrap a function to accept a list of string shell-style arguments, parse them, and
    call the original function.
    """
    params = inspect_function_params(func)
    pos_params = [p for p in params if p.is_positional]
    kw_params = [p for p in params if p not in pos_params]

    @wraps(func)
    def wrapped(args: List[str]) -> Optional[R]:
        shell_args = parse_shell_args(args)

        if shell_args.show_help:
            print_command_function_help(cast(CommandFunction, func), verbose=True)
            return None
        elif shell_args.options.get("show_source", False):
            help_commands.source_code(func.__name__)
            return None

        pos_values, kw_consumed = _map_positional(shell_args.args, pos_params, kw_params)

        # If some positional arguments were used as keyword arguments, we need to remove
        # them from the kw_params so they don't get passed twice.
        remaining_kw_params = kw_params[kw_consumed:]

        kw_values = _map_keyword(shell_args.options, remaining_kw_params)

        if args:
            log.info(
                "Mapping shell args to function params: %s -> %s -> %s(*%s, **%s)",
                args,
                shell_args,
                func.__name__,
                pos_values,
                kw_values,
            )

        return func(*pos_values, **kw_values)

    return wrapped


## Tests


def test_wrap_function():
    def func1(
        arg1: str, arg2: str, arg3: int, option_one: bool = False, option_two: Optional[str] = None
    ) -> List:
        return [arg1, arg2, arg3, option_one, option_two]

    def func2(
        *paths: str, summary: Optional[bool] = False, iso_time: Optional[bool] = False
    ) -> List:
        return [paths, summary, iso_time]

    def func3(arg1: str, **keywords) -> List:
        return [arg1, keywords]

    def func4() -> List:
        return []

    wrapped_func1 = wrap_for_shell_args(func1)
    wrapped_func2 = wrap_for_shell_args(func2)
    wrapped_func3 = wrap_for_shell_args(func3)
    wrapped_func4 = wrap_for_shell_args(func4)

    print("\nwrapped:")
    print(
        wrapped_func1(["arg1_value", "arg2_value", "99", "--option_one", "--option_two=some_value"])
    )
    print(wrapped_func2(["--summary", "--iso_time", "path1", "path2", "path3"]))
    print(wrapped_func3(["arg1_value", "--extra_param=some_value"]))

    print(wrapped_func4([]))

    assert wrapped_func1(
        ["arg1_value", "arg2_value", "99", "--option_one", "--option_two=some_value"]
    ) == [
        "arg1_value",
        "arg2_value",
        99,
        True,
        "some_value",
    ]
    assert wrapped_func2(["--summary", "--iso_time", "path1", "path2", "path3"]) == [
        ("path1", "path2", "path3"),
        True,
        True,
    ]
    assert wrapped_func3(["arg1_value", "--extra_param=some_value"]) == [
        "arg1_value",
        {"extra_param": "some_value"},
    ]
    assert wrapped_func4([]) == []
