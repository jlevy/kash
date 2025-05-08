import inspect
import types
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from inspect import Parameter
from typing import Any, Union, cast, get_args, get_origin  # pyright: ignore[reportDeprecated]

NO_DEFAULT = Parameter.empty  # Alias for clarity

ParameterKind = Parameter.POSITIONAL_ONLY.__class__


@dataclass(frozen=True)
class FuncParam:
    """
    Hold structured information about a single function parameter.
    """

    name: str
    kind: ParameterKind  # e.g., POSITIONAL_OR_KEYWORD
    annotation: Any  # The raw type annotation (can be Parameter.empty)
    default: Any  # The raw default value (can be Parameter.empty)
    position: int | None  # Position index for positional args, None for keyword-only

    # Resolved type information
    # This is the concrete, simplified main type (e.g., str from str | None, list from list[int])
    effective_type: type | None
    inner_type: type | None  # For collections, the type of elements (e.g., str from list[str])
    is_explicitly_optional: bool  # True if original annotation was Optional[X] or X | None

    @property
    def has_default(self) -> bool:
        """Does this parameter have a default value?"""
        return self.default != NO_DEFAULT

    @property
    def is_pure_positional(self) -> bool:
        """Is this a plain or varargs positional parameter, with no default value?"""
        return self.position is not None and not self.has_default

    @property
    def is_positional_only(self) -> bool:
        """Is a true positional parameter, with no default value."""
        return self.kind == Parameter.POSITIONAL_ONLY

    @property
    def is_positional_or_keyword(self) -> bool:
        return self.kind == Parameter.POSITIONAL_OR_KEYWORD

    @property
    def is_varargs(self) -> bool:
        return self.kind == Parameter.VAR_POSITIONAL or self.kind == Parameter.VAR_KEYWORD

    @property
    def is_keyword_only(self) -> bool:
        return self.kind == Parameter.KEYWORD_ONLY


def _resolve_type_details(annotation: Any) -> tuple[type | None, type | None, bool]:
    """
    Resolves an annotation into (effective_type, inner_type, is_explicitly_optional).

    - effective_type: The main type (e.g., str from Optional[str], list from list[int]).
    - inner_type: The type of elements if effective_type is a collection
                  (e.g., int from list[int]). For non-collection or unparameterized
                  collection, this is None.
    - is_explicitly_optional: True if the annotation was X | None or Optional[X].
    """
    if annotation is Parameter.empty or annotation is Any:
        return (None, None, False)

    current_annotation = annotation
    is_optional_flag = False

    # Unwrap Optional[T] or T | None (from Python 3.10+ UnionType)
    origin: type | None = get_origin(current_annotation)
    args = get_args(current_annotation)

    if origin is Union or (  # pyright: ignore[reportDeprecated]
        hasattr(types, "UnionType") and isinstance(current_annotation, types.UnionType)
    ):
        non_none_args = [arg for arg in args if arg is not type(None)]
        if len(non_none_args) == 1:
            is_optional_flag = True
            current_annotation = non_none_args[0]
            origin = get_origin(current_annotation)  # Re-evaluate for the unwrapped type
            args = get_args(current_annotation)
        elif not non_none_args:  # Handles Union[NoneType] or just NoneType
            return (type(None), None, True)
        # If multiple non_none_args (e.g., int | str), current_annotation remains the Union for now.

    #  Determine effective_type and inner_type from (potentially unwrapped) current_annotation
    final_effective_type: type | None = None
    final_inner_type: type | None = None

    if isinstance(
        current_annotation, type
    ):  # Covers simple types (int, str) and resolved Union types (int | str)
        final_effective_type = current_annotation
    elif origin and isinstance(origin, type):  # Generics like list, dict, tuple (e.g., list[str])
        final_effective_type = cast(type, origin)  # This would be `list` for `list[str]`
        if args and _is_type_tuple(args) and args[0] is not Any:
            # For simplicity, take the first type argument as inner_type.
            # E.g., for list[str], inner_type is str. For dict[str, int], inner_type is str.
            final_inner_type = args[0]
            # A more sophisticated approach might handle all args for tuples like tuple[str, int]

    return final_effective_type, final_inner_type, is_optional_flag


def _is_type_tuple(args: tuple[Any, ...]) -> bool:
    """Are all args types?"""
    if not args:
        return False
    return all(isinstance(arg, type) for arg in args)


def inspect_function_params(func: Callable[..., Any], unwrap: bool = True) -> list[FuncParam]:
    """
    Inspects a Python function's signature and returns a list of `ParamInfo` objects.
    A convenience wrapper for `inspect.signature` that provides a detailed, structured
    representation of each parameter, making it easier to build tools like CLI argument
    parsers. By default, it unwraps decorated functions to get to the original signature.
    """
    unwrapped_func = inspect.unwrap(func) if unwrap else func
    signature = inspect.signature(unwrapped_func)

    param_infos: list[FuncParam] = []

    for i, (param_name, param_obj) in enumerate(signature.parameters.items()):
        effective_type, inner_type, is_optional = _resolve_type_details(param_obj.annotation)

        # Fallback: if type is not resolved from annotation, try to infer from default value.
        if (
            effective_type is None
            and param_obj.default is not NO_DEFAULT
            and param_obj.default is not None
        ):
            if not is_optional:  # Avoid setting NoneType if it was Optional[SomethingElse]
                effective_type = type(param_obj.default)

        # Determine position
        is_positional = param_obj.kind in (
            Parameter.POSITIONAL_ONLY,
            Parameter.POSITIONAL_OR_KEYWORD,
            Parameter.VAR_POSITIONAL,
        )
        position = i + 1 if is_positional else None

        info = FuncParam(
            name=param_name,
            kind=param_obj.kind,
            annotation=param_obj.annotation,  # Store raw annotation
            default=param_obj.default,  # Store raw default
            position=position,
            effective_type=effective_type,
            inner_type=inner_type,
            is_explicitly_optional=is_optional,
        )
        param_infos.append(info)

    return param_infos


## Tests


def test_inspect_function_parameters_updated():
    # Test functions from your original example
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

    def func5(x: int, y: int = 3, *, z: int = 4, **kwargs):
        return [x, y, z, kwargs]

    class MyEnum(Enum):
        ITEM1 = "item1"
        ITEM2 = "item2"

    def func6(opt_enum: MyEnum | None = MyEnum.ITEM1):
        return [opt_enum]

    def func7(numbers: list[int]):
        return [numbers]

    def func8(maybe_list: list[str] | None = None):
        return [maybe_list]

    params0 = inspect_function_params(func0)
    print("\ninspect_function_parameters results:")
    print(f"func0: {params0}")
    assert params0 == [
        FuncParam(
            name="path",
            kind=Parameter.POSITIONAL_OR_KEYWORD,
            annotation=(str | None),
            default=None,
            position=1,
            effective_type=str,
            inner_type=None,
            is_explicitly_optional=True,
        )
    ]

    params1 = inspect_function_params(func1)
    print(f"func1: {params1}")
    assert params1 == [
        FuncParam(
            name="arg1",
            kind=Parameter.POSITIONAL_OR_KEYWORD,
            annotation=str,
            default=NO_DEFAULT,
            position=1,
            effective_type=str,
            inner_type=None,
            is_explicitly_optional=False,
        ),
        FuncParam(
            name="arg2",
            kind=Parameter.POSITIONAL_OR_KEYWORD,
            annotation=str,
            default=NO_DEFAULT,
            position=2,
            effective_type=str,
            inner_type=None,
            is_explicitly_optional=False,
        ),
        FuncParam(
            name="arg3",
            kind=Parameter.POSITIONAL_OR_KEYWORD,
            annotation=int,
            default=NO_DEFAULT,
            position=3,
            effective_type=int,
            inner_type=None,
            is_explicitly_optional=False,
        ),
        FuncParam(
            name="option_one",
            kind=Parameter.POSITIONAL_OR_KEYWORD,
            annotation=bool,
            default=False,
            position=4,
            effective_type=bool,
            inner_type=None,
            is_explicitly_optional=False,
        ),  # bool default makes it not explicitly Optional from type
        FuncParam(
            name="option_two",
            kind=Parameter.POSITIONAL_OR_KEYWORD,
            annotation=(str | None),
            default=None,
            position=5,
            effective_type=str,
            inner_type=None,
            is_explicitly_optional=True,
        ),
    ]

    params2 = inspect_function_params(func2)
    print(f"func2: {params2}")
    assert params2 == [
        FuncParam(
            name="paths",
            kind=Parameter.VAR_POSITIONAL,
            annotation=str,
            default=NO_DEFAULT,
            position=1,
            effective_type=str,
            inner_type=None,
            is_explicitly_optional=False,
        ),  # For *args: T, effective_type is T
        FuncParam(
            name="summary",
            kind=Parameter.KEYWORD_ONLY,
            annotation=(bool | None),
            default=False,
            position=None,
            effective_type=bool,
            inner_type=None,
            is_explicitly_optional=True,
        ),
        FuncParam(
            name="iso_time",
            kind=Parameter.KEYWORD_ONLY,
            annotation=bool,
            default=False,
            position=None,
            effective_type=bool,
            inner_type=None,
            is_explicitly_optional=False,
        ),
    ]

    params3 = inspect_function_params(func3)
    print(f"func3: {params3}")
    assert params3 == [
        FuncParam(
            name="arg1",
            kind=Parameter.POSITIONAL_OR_KEYWORD,
            annotation=str,
            default=NO_DEFAULT,
            position=1,
            effective_type=str,
            inner_type=None,
            is_explicitly_optional=False,
        ),
        FuncParam(
            name="keywords",
            kind=Parameter.VAR_KEYWORD,
            annotation=Parameter.empty,
            default=NO_DEFAULT,
            position=None,
            effective_type=None,
            inner_type=None,
            is_explicitly_optional=False,
        ),
    ]

    params4 = inspect_function_params(func4)
    print(f"func4: {params4}")
    assert params4 == []

    params5 = inspect_function_params(func5)
    print(f"func5: {params5}")
    assert params5 == [
        FuncParam(
            name="x",
            kind=Parameter.POSITIONAL_OR_KEYWORD,
            annotation=int,
            default=NO_DEFAULT,
            position=1,
            effective_type=int,
            inner_type=None,
            is_explicitly_optional=False,
        ),
        FuncParam(
            name="y",
            kind=Parameter.POSITIONAL_OR_KEYWORD,
            annotation=int,
            default=3,
            position=2,
            effective_type=int,
            inner_type=None,
            is_explicitly_optional=False,
        ),
        FuncParam(
            name="z",
            kind=Parameter.KEYWORD_ONLY,
            annotation=int,
            default=4,
            position=None,
            effective_type=int,
            inner_type=None,
            is_explicitly_optional=False,
        ),
        FuncParam(
            name="kwargs",
            kind=Parameter.VAR_KEYWORD,
            annotation=Parameter.empty,
            default=NO_DEFAULT,
            position=None,
            effective_type=None,
            inner_type=None,
            is_explicitly_optional=False,
        ),
    ]

    params6 = inspect_function_params(func6)
    print(f"func6: {params6}")

    assert params6 == [
        FuncParam(
            name="opt_enum",
            kind=Parameter.POSITIONAL_OR_KEYWORD,
            annotation=(MyEnum | None),
            default=MyEnum.ITEM1,
            position=1,
            effective_type=MyEnum,
            inner_type=None,
            is_explicitly_optional=True,
        )
    ]

    params7 = inspect_function_params(func7)
    print(f"func7: {params7}")
    assert params7 == [
        FuncParam(
            name="numbers",
            kind=Parameter.POSITIONAL_OR_KEYWORD,
            annotation=list[int],
            default=NO_DEFAULT,
            position=1,
            effective_type=list,
            inner_type=int,
            is_explicitly_optional=False,
        )
    ]

    params8 = inspect_function_params(func8)
    print(f"func8: {params8}")
    assert params8 == [
        FuncParam(
            name="maybe_list",
            kind=Parameter.POSITIONAL_OR_KEYWORD,
            annotation=(list[str] | None),
            default=None,
            position=1,
            effective_type=list,
            inner_type=str,
            is_explicitly_optional=True,
        )
    ]
