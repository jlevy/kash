import inspect
import types
from collections.abc import Callable
from dataclasses import dataclass
from inspect import Parameter
from typing import Any, Union, cast, get_args, get_origin  # pyright: ignore

NO_DEFAULT = Parameter.empty


@dataclass(frozen=True)
class FuncParam:
    name: str
    type: type | None
    default: Any
    position: int | None
    is_varargs: bool

    @property
    def is_positional(self) -> bool:
        """Is this a purely positional parameter, with no default value?"""
        return self.position is not None and not self.has_default

    @property
    def has_default(self) -> bool:
        """Does this parameter have a default value?"""
        return self.default != NO_DEFAULT


def inspect_function_params(func: Callable[..., Any], unwrap: bool = True) -> list[FuncParam]:
    """
    Get names and types of parameters on a Python function. Just a convenience wrapper
    around `inspect.signature` to give parameter names, types, and default values.

    It also parses `Optional` types to return the underlying type and unwraps
    decorated functions to get the underlying parameters. Returns a list of
    `FuncParam` values.

    Note that technically, parameters are of 5 types, positional-only,
    positional-or-keyword, keyword-only, varargs, or varargs-keyword, which is what
    `inspect` tells you, but in practice you typically just want to know
    `FuncParam.is_positional()`, i.e. if it is a pure positional parameter (no default)
    and not a keyword (with a default).
    """
    unwrapped = inspect.unwrap(func) if unwrap else func
    signature = inspect.signature(unwrapped)
    params: list[FuncParam] = []

    for i, param in enumerate(signature.parameters.values()):
        is_positional = param.kind in (
            Parameter.POSITIONAL_ONLY,
            Parameter.POSITIONAL_OR_KEYWORD,
            Parameter.VAR_POSITIONAL,
        )
        is_varargs = param.kind in (Parameter.VAR_POSITIONAL, Parameter.VAR_KEYWORD)
        has_default = param.default != NO_DEFAULT

        # Get type from type annotation or default value.
        param_type: type | None = None
        if param.annotation != Parameter.empty:
            param_type = _extract_simple_type(param.annotation)
        elif param.default is not Parameter.empty:
            param_type = type(param.default)

        func_param = FuncParam(
            name=param.name,
            type=param_type,
            default=param.default if has_default else NO_DEFAULT,
            position=i + 1 if is_positional else None,
            is_varargs=is_varargs,
        )
        params.append(func_param)

    return params


def _extract_simple_type(annotation: Any) -> type | None:
    """
    Extract a single Type from an annotation that is an explicit simple type (like `str` or
    an enum) or a simple Union (such as `str` from `Optional[str]`). Return None if it's not
    clear.
    """
    if isinstance(annotation, type):
        return annotation

    # Handle pipe syntax (str | None) from Python 3.10+
    if hasattr(types, "UnionType") and isinstance(annotation, types.UnionType):
        args = get_args(annotation)
        non_none_args = [arg for arg in args if arg is not type(None)]
        if len(non_none_args) == 1 and isinstance(non_none_args[0], type):
            return non_none_args[0]

    origin = get_origin(annotation)
    if origin is Union:  # pyright: ignore
        args = get_args(annotation)
        non_none_args = [arg for arg in args if arg is not type(None)]
        if len(non_none_args) == 1 and isinstance(non_none_args[0], type):
            return non_none_args[0]
    elif origin and isinstance(origin, type):
        # Cast origin to type to satisfy the type checker
        return cast(type, origin)  # pyright: ignore

    return None


## Tests


def test_inspect_function_params():
    def func0(path: str | None = None) -> list:
        return [path]

    def func1(
        arg1: str, arg2: str, arg3: int, option_one: bool = False, option_two: str | None = None
    ) -> list:
        return [arg1, arg2, arg3, option_one, option_two]

    def func2(*paths: str, summary: bool | None = False, iso_time: bool = False) -> list:
        return [paths, summary, iso_time]

    def func3(arg1: str, **keywords) -> list:
        return [arg1, keywords]

    def func4() -> list:
        return []

    def func5(x: int, y: int = 3, *, z: int = 4, **kwargs):  # pyright: ignore[reportUnusedParameter]
        pass

    params0 = inspect_function_params(func0)
    params1 = inspect_function_params(func1)
    params2 = inspect_function_params(func2)
    params3 = inspect_function_params(func3)
    params4 = inspect_function_params(func4)
    params5 = inspect_function_params(func5)

    print("\ninspect:")
    print(repr(params0))
    print()
    print(repr(params1))
    print()
    print(repr(params2))
    print()
    print(repr(params3))
    print()
    print(repr(params4))
    print()
    print(repr(params5))

    assert params0 == [FuncParam(name="path", type=str, default=None, position=1, is_varargs=False)]

    assert params1 == [
        FuncParam(name="arg1", type=str, default=NO_DEFAULT, position=1, is_varargs=False),
        FuncParam(name="arg2", type=str, default=NO_DEFAULT, position=2, is_varargs=False),
        FuncParam(name="arg3", type=int, default=NO_DEFAULT, position=3, is_varargs=False),
        FuncParam(name="option_one", type=bool, default=False, position=4, is_varargs=False),
        FuncParam(name="option_two", type=str, default=None, position=5, is_varargs=False),
    ]

    assert params2 == [
        FuncParam(name="paths", type=str, default=NO_DEFAULT, position=1, is_varargs=True),
        FuncParam(name="summary", type=bool, default=False, position=None, is_varargs=False),
        FuncParam(name="iso_time", type=bool, default=False, position=None, is_varargs=False),
    ]

    assert params3 == [
        FuncParam(name="arg1", type=str, default=NO_DEFAULT, position=1, is_varargs=False),
        FuncParam(name="keywords", type=None, default=NO_DEFAULT, position=None, is_varargs=True),
    ]

    assert params4 == []

    assert params5 == [
        FuncParam(name="x", type=int, default=NO_DEFAULT, position=1, is_varargs=False),
        FuncParam(name="y", type=int, default=3, position=2, is_varargs=False),
        FuncParam(name="z", type=int, default=4, position=None, is_varargs=False),
        FuncParam(name="kwargs", type=None, default=NO_DEFAULT, position=None, is_varargs=True),
    ]
