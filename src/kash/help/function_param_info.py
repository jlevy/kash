from collections.abc import Callable
from dataclasses import replace
from typing import Any

from kash.help.docstring_utils import parse_docstring
from kash.model.params_model import ALL_COMMON_PARAMS, Param
from kash.utils.common.function_inspect import FuncParam, inspect_function_params


def _look_up_param_docs(func: Callable[..., Any], kw_params: list[FuncParam]) -> list[Param]:
    def look_up(func: Callable[..., Any], func_param: FuncParam) -> Param:
        name = func_param.name
        param = ALL_COMMON_PARAMS.get(name)
        if not param:
            param = Param(name, description=None, type=func_param.type or str)

        # Also check the docstring for a description of this parameter.
        docstring = parse_docstring(func.__doc__ or "")
        docstring_params = docstring.param

        if name in docstring_params:
            param = replace(param, description=docstring_params[name])

        return param

    return [look_up(func, func_param) for func_param in kw_params]


def annotate_param_info(func: Callable[..., Any]) -> list[Param]:
    """
    Inspect the types on the positional and keyword parameters for a function,
    as well as docs for them.

    Matches param info by looking for parameters of the same name from the
    global parameter docs as well. Also look at docstrings with parameter info.

    Cache the result on the function's `__param_info__` attribute.
    """
    if not hasattr(func, "__param_info__"):
        params = inspect_function_params(func)
        param_info = _look_up_param_docs(func, params)
        func.__param_info__ = param_info  # pyright: ignore

    return func.__param_info__  # pyright: ignore
